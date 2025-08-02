# --- pnl_calculator.py ---
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timezone
from typing import Optional, Dict, List
from domain.models import (
    WebhookTrade, WebhookPosition, WebhookPnlSummary, 
    User, WebhookConfig
)
from infrastructure.external.hyperliquid_client import HyperliquidClient

class PnlCalculator:
    def __init__(self, db: Session):
        self.db = db
    
    def record_trade(
        self,
        webhook_config_id: int,
        user_id: int,
        asset_name: str,
        trade_type: str,  # BUY, SELL, CLOSE, DCA, REDUCE
        side: str,        # LONG, SHORT
        quantity: float,
        price: float,
        usd_value: float,
        leverage: int,
        order_id: Optional[str] = None,
        fees: float = 0.0
    ) -> WebhookTrade:
        """Registra um novo trade e atualiza posições e PNL"""
        
        # Criar registro do trade
        trade = WebhookTrade(
            webhook_config_id=webhook_config_id,
            user_id=user_id,
            asset_name=asset_name,
            trade_type=trade_type,
            side=side,
            quantity=quantity,
            price=price,
            usd_value=usd_value,
            leverage=leverage,
            order_id=order_id,
            fees=fees,
            timestamp=datetime.now(timezone.utc)
        )
        
        self.db.add(trade)
        self.db.flush()
        
        # Atualizar posição
        self._update_position(trade)
        
        # Atualizar resumo PNL
        self._update_pnl_summary(user_id, asset_name)
        
        self.db.commit()
        
        return trade
    
    def _update_position(self, trade: WebhookTrade):
        """Atualiza a posição baseada no trade"""
        
        if trade.trade_type == "CLOSE":
            position = self.db.query(WebhookPosition).filter(
                and_(
                    WebhookPosition.webhook_config_id == trade.webhook_config_id,
                    WebhookPosition.asset_name == trade.asset_name,
                    WebhookPosition.is_open == True
                )
            ).first()
            
            if position:
                position.is_open = False
                position.closed_at = trade.timestamp
                position.realized_pnl = self._calculate_realized_pnl(
                    position.quantity, position.avg_entry_price, 
                    trade.quantity, trade.price, position.side
                )
                position.total_fees += trade.fees
                self.db.flush()
                
        elif trade.trade_type in ["BUY", "SELL"]:
            # Para outros tipos de trade, buscar posição com side específico
            position = self.db.query(WebhookPosition).filter(
                and_(
                    WebhookPosition.webhook_config_id == trade.webhook_config_id,
                    WebhookPosition.asset_name == trade.asset_name,
                    WebhookPosition.side == trade.side,
                    WebhookPosition.is_open == True
                )
            ).first()
            # Nova posição
            if not position:
                position = WebhookPosition(
                    webhook_config_id=trade.webhook_config_id,
                    user_id=trade.user_id,
                    asset_name=trade.asset_name,
                    side=trade.side,
                    quantity=trade.quantity,
                    avg_entry_price=trade.price,
                    leverage=trade.leverage,
                    total_fees=trade.fees,
                    opened_at=trade.timestamp,
                    last_updated=trade.timestamp
                )
                self.db.add(position)
            else:
                # Atualizar posição existente (DCA)
                self._update_position_dca(position, trade)
        
        elif trade.trade_type == "DCA":
            # Dollar Cost Average - aumentar posição
            position = self.db.query(WebhookPosition).filter(
                and_(
                    WebhookPosition.webhook_config_id == trade.webhook_config_id,
                    WebhookPosition.asset_name == trade.asset_name,
                    WebhookPosition.side == trade.side,
                    WebhookPosition.is_open == True
                )
            ).first()
            
            if position:
                self._update_position_dca(position, trade)
            else:
                # Se não há posição, criar nova (DCA pode ser entrada inicial)
                position = WebhookPosition(
                    webhook_config_id=trade.webhook_config_id,
                    user_id=trade.user_id,
                    asset_name=trade.asset_name,
                    side=trade.side,
                    quantity=trade.quantity,
                    avg_entry_price=trade.price,
                    leverage=trade.leverage,
                    total_fees=trade.fees,
                    opened_at=trade.timestamp,
                    last_updated=trade.timestamp
                )
                self.db.add(position)
        
        elif trade.trade_type == "REDUCE":
            # Reduzir posição
            position = self.db.query(WebhookPosition).filter(
                and_(
                    WebhookPosition.webhook_config_id == trade.webhook_config_id,
                    WebhookPosition.asset_name == trade.asset_name,
                    WebhookPosition.side == trade.side,
                    WebhookPosition.is_open == True
                )
            ).first()
            
            if position:
                self._reduce_position(position, trade)
            else:
                # Se não há posição para reduzir, tratar como fechamento de posição implícita
                # Criar uma posição temporária para calcular o PNL
                position = WebhookPosition(
                    webhook_config_id=trade.webhook_config_id,
                    user_id=trade.user_id,
                    asset_name=trade.asset_name,
                    side=trade.side,
                    quantity=trade.quantity,
                    avg_entry_price=trade.price,  # Assumir preço atual como base
                    leverage=trade.leverage,
                    total_fees=trade.fees,
                    realized_pnl=0.0,  # Sem PNL se não há histórico
                    is_open=False,  # Já fechada
                    opened_at=trade.timestamp,
                    closed_at=trade.timestamp,
                    last_updated=trade.timestamp
                )
                self.db.add(position)
        
        self.db.commit()
    
    def _update_position_dca(self, position: WebhookPosition, trade: WebhookTrade):
        """Atualiza posição com DCA (Dollar Cost Average)"""
        
        # Calcular novo preço médio
        total_value_old = position.quantity * position.avg_entry_price
        total_value_new = trade.quantity * trade.price
        new_quantity = position.quantity + trade.quantity
        
        if new_quantity > 0:
            position.avg_entry_price = (total_value_old + total_value_new) / new_quantity
            position.quantity = new_quantity
        
        position.total_fees += trade.fees
        position.last_updated = trade.timestamp
    
    def _reduce_position(self, position: WebhookPosition, trade: WebhookTrade):
        """Reduz uma posição existente"""
        
        # Calcular PNL realizado da parte fechada
        realized_pnl = self._calculate_realized_pnl(
            trade.quantity, position.avg_entry_price,
            trade.quantity, trade.price, position.side
        )
        
        position.realized_pnl += realized_pnl
        position.quantity -= trade.quantity
        position.total_fees += trade.fees
        position.last_updated = trade.timestamp
        
        # Se quantidade chegou a zero, fechar posição
        if position.quantity <= 0:
            position.is_open = False
            position.closed_at = trade.timestamp
    
    def _calculate_realized_pnl(
        self, 
        quantity: float, 
        entry_price: float, 
        exit_quantity: float, 
        exit_price: float, 
        side: str
    ) -> float:
        """Calcula PNL realizado"""
        
        if side == "LONG":
            return exit_quantity * (exit_price - entry_price)
        else:  # SHORT
            return exit_quantity * (entry_price - exit_price)
    
    def _update_pnl_summary(self, user_id: int, asset_name: str):
        """Atualiza o resumo de PNL para um ativo"""
        
        # Buscar ou criar resumo
        summary = self.db.query(WebhookPnlSummary).filter(
            and_(
                WebhookPnlSummary.user_id == user_id,
                WebhookPnlSummary.asset_name == asset_name
            )
        ).first()
        
        if not summary:
            summary = WebhookPnlSummary(
                user_id=user_id,
                asset_name=asset_name
            )
            self.db.add(summary)
        
        # Calcular estatísticas dos trades
        trades = self.db.query(WebhookTrade).filter(
            and_(
                WebhookTrade.user_id == user_id,
                WebhookTrade.asset_name == asset_name
            )
        ).all()
        
        # Calcular PNL das posições
        positions = self.db.query(WebhookPosition).filter(
            and_(
                WebhookPosition.user_id == user_id,
                WebhookPosition.asset_name == asset_name
            )
        ).all()
        
        # Estatísticas básicas
        summary.total_trades = len(trades)
        summary.total_realized_pnl = sum(p.realized_pnl or 0 for p in positions)
        summary.total_unrealized_pnl = sum(p.unrealized_pnl or 0 for p in positions if p.is_open)
        summary.total_fees = sum(t.fees for t in trades)
        summary.total_volume = sum(t.usd_value for t in trades)
        
        # CORREÇÃO: Calcular trades vencedores e perdedores baseado em CICLOS COMPLETOS
        # Um ciclo completo = abertura + possíveis DCAs + fechamento
        closed_positions = [p for p in positions if not p.is_open]
        
        # Separar por PNL realizado
        winning_positions = [p for p in closed_positions if (p.realized_pnl or 0) > 0]
        losing_positions = [p for p in closed_positions if (p.realized_pnl or 0) < 0]
        neutral_positions = [p for p in closed_positions if (p.realized_pnl or 0) == 0]
        
        # NOVA LÓGICA MELHORADA: Usar análise de sequências de trades
        sequences_analysis = self._analyze_trade_sequences(user_id, asset_name)
        
        # Priorizar análise de sequências se houver dados suficientes
        if sequences_analysis["total_sequences"] > 0:
            summary.winning_trades = sequences_analysis["winning_trades"]
            summary.losing_trades = sequences_analysis["losing_trades"]
            print(f"📊 Usando análise de sequências: {summary.winning_trades} vencedoras, {summary.losing_trades} perdedoras")
        else:
            # Fallback para método original (baseado em posições)
            summary.winning_trades = len(winning_positions)
            summary.losing_trades = len(losing_positions)
            print(f"📊 Usando análise de posições: {summary.winning_trades} vencedoras, {summary.losing_trades} perdedoras")
        
        # ADICIONAL: Para melhor precisão, também contar trades de fechamento/redução como trades individuais
        # se não houver posições registradas (fallback para compatibilidade)
        if len(closed_positions) == 0 and sequences_analysis["total_sequences"] == 0:
            # Fallback: contar trades de fechamento como trades individuais
            closing_trades = [t for t in trades if t.trade_type in ["CLOSE", "REDUCE"]]
            if closing_trades:
                # Assumir que trades de fechamento com PNL positivo são vencedores
                # (isso requer que o PNL seja calculado no momento do trade)
                for trade in closing_trades:
                    # Estimar se o trade foi positivo baseado no preço médio
                    # Esta é uma estimativa - idealmente o PNL deveria estar no trade
                    summary.winning_trades += 1  # Placeholder - precisa de lógica mais sofisticada
        
        # Calcular métricas
        total_closed_trades = summary.winning_trades + summary.losing_trades
        if total_closed_trades > 0:
            summary.win_rate = (summary.winning_trades / total_closed_trades) * 100
        else:
            summary.win_rate = 0
        
        if winning_positions:
            summary.avg_win = sum(p.realized_pnl or 0 for p in winning_positions) / len(winning_positions)
            summary.largest_win = max(p.realized_pnl or 0 for p in winning_positions)
        else:
            summary.avg_win = 0
            summary.largest_win = 0
        
        if losing_positions:
            summary.avg_loss = sum(p.realized_pnl or 0 for p in losing_positions) / len(losing_positions)
            summary.largest_loss = min(p.realized_pnl or 0 for p in losing_positions)
        else:
            summary.avg_loss = 0
            summary.largest_loss = 0
        
        # PNL líquido
        summary.net_pnl = summary.total_realized_pnl + summary.total_unrealized_pnl - summary.total_fees
        summary.last_updated = datetime.now(timezone.utc)
        
        print(f"📊 PNL SUMMARY ATUALIZADO para {asset_name}:")
        print(f"  Total trades (execuções): {summary.total_trades}")
        print(f"  Posições fechadas: {len(closed_positions)}")
        print(f"  Trades vencedores: {summary.winning_trades}")
        print(f"  Trades perdedores: {summary.losing_trades}")
        print(f"  Win rate: {summary.win_rate:.1f}%")
        print(f"  PNL realizado: ${summary.total_realized_pnl:.2f}")
        print(f"  PNL líquido: ${summary.net_pnl:.2f}")
        
        self.db.commit()
    
    def update_unrealized_pnl(self, user_id: int, client: HyperliquidClient):
        """Atualiza PNL não realizado de todas as posições abertas"""
        
        open_positions = self.db.query(WebhookPosition).filter(
            and_(
                WebhookPosition.user_id == user_id,
                WebhookPosition.is_open == True
            )
        ).all()
        
        for position in open_positions:
            try:
                # Obter preço atual
                current_price = client.get_asset_price(position.asset_name)
                if current_price:
                    position.current_price = current_price
                    
                    # Calcular PNL não realizado
                    if position.side == "LONG":
                        position.unrealized_pnl = position.quantity * (current_price - position.avg_entry_price)
                    else:  # SHORT
                        position.unrealized_pnl = position.quantity * (position.avg_entry_price - current_price)
                    
                    position.last_updated = datetime.now(timezone.utc)
            
            except Exception as e:
                print(f"Erro ao atualizar preço para {position.asset_name}: {e}")
        
        self.db.commit()
        
        # Atualizar resumos PNL
        assets = set(p.asset_name for p in open_positions)
        for asset in assets:
            self._update_pnl_summary(user_id, asset)
    
    def get_pnl_by_period(
        self, 
        user_id: int, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict:
        """Obtém PNL por período"""
        
        trades = self.db.query(WebhookTrade).filter(
            and_(
                WebhookTrade.user_id == user_id,
                WebhookTrade.timestamp >= start_date,
                WebhookTrade.timestamp <= end_date
            )
        ).all()
        
        positions_closed = self.db.query(WebhookPosition).filter(
            and_(
                WebhookPosition.user_id == user_id,
                WebhookPosition.closed_at >= start_date,
                WebhookPosition.closed_at <= end_date,
                WebhookPosition.is_open == False
            )
        ).all()
        
        total_realized_pnl = sum(p.realized_pnl for p in positions_closed)
        total_fees = sum(t.fees for t in trades)
        total_trades = len(trades)
        
        return {
            "period_pnl": total_realized_pnl - total_fees,
            "period_trades": total_trades,
            "total_fees": total_fees,
            "realized_pnl": total_realized_pnl
        }
    
    def recalculate_all_pnl_summaries(self, user_id: int):
        """
        Recalcula todos os resumos de PNL para um usuário
        Útil para corrigir dados após mudanças na lógica de cálculo
        """
        print(f"🔄 RECALCULANDO TODOS OS PNLs para usuário {user_id}")
        
        # Buscar todos os assets que o usuário tem trades
        assets = self.db.query(WebhookTrade.asset_name).filter(
            WebhookTrade.user_id == user_id
        ).distinct().all()
        
        for (asset_name,) in assets:
            print(f"\n📊 Recalculando PNL para {asset_name}...")
            self._reprocess_asset_trades(user_id, asset_name)
            self._update_pnl_summary(user_id, asset_name)
        
        print(f"✅ Recálculo completo para {len(assets)} assets")
    
    def _reprocess_asset_trades(self, user_id: int, asset_name: str):
        """
        Reprocessa todos os trades de um ativo para corrigir posições que não foram calculadas corretamente
        """
        print(f"🔄 Reprocessando trades para {asset_name}...")
        
        # Buscar todos os trades do ativo ordenados por data
        trades = self.db.query(WebhookTrade).filter(
            and_(
                WebhookTrade.user_id == user_id,
                WebhookTrade.asset_name == asset_name
            )
        ).order_by(WebhookTrade.timestamp).all()
        
        # Limpar posições existentes para recriar
        existing_positions = self.db.query(WebhookPosition).filter(
            and_(
                WebhookPosition.user_id == user_id,
                WebhookPosition.asset_name == asset_name
            )
        ).all()
        
        for position in existing_positions:
            self.db.delete(position)
        
        self.db.flush()
        
        # Reprocessar cada trade para recriar as posições corretamente
        for trade in trades:
            print(f"  📈 Reprocessando trade {trade.id}: {trade.trade_type} {trade.side} {trade.quantity}")
            self._update_position(trade)
        
        self.db.commit()
        print(f"✅ Reprocessamento completo para {asset_name}: {len(trades)} trades processados")
    
    def get_assets_pnl_summary(self, user_id: int) -> List[WebhookPnlSummary]:
        """Obtém resumo de PNL por ativo"""
        
        return self.db.query(WebhookPnlSummary).filter(
            WebhookPnlSummary.user_id == user_id
        ).all()
    
    def _analyze_trade_sequences(self, user_id: int, asset_name: str) -> Dict:
        """
        Analisa sequências de trades para calcular corretamente trades vencedores/perdedores
        Uma sequência = abertura + DCAs + fechamento = 1 trade completo
        """
        
        trades = self.db.query(WebhookTrade).filter(
            and_(
                WebhookTrade.user_id == user_id,
                WebhookTrade.asset_name == asset_name
            )
        ).order_by(WebhookTrade.timestamp).all()
        
        if not trades:
            return {"winning_trades": 0, "losing_trades": 0, "total_sequences": 0}
        
        sequences = []
        current_sequence = []
        
        print(f"🔍 ANALISANDO {len(trades)} trades para {asset_name}:")
        
        for trade in trades:
            print(f"  {trade.timestamp.strftime('%d/%m %H:%M')} - {trade.trade_type} {trade.side} - {trade.quantity} @ ${trade.price:.4f}")
            
            current_sequence.append(trade)
            
            # Uma sequência termina com fechamento ou redução total
            if trade.trade_type in ["CLOSE", "REDUCE"]:
                if current_sequence:
                    sequences.append(current_sequence.copy())
                    print(f"    ✅ Sequência finalizada com {len(current_sequence)} trades")
                    current_sequence = []
        
        # Se há trades pendentes (posição ainda aberta), adicionar como sequência incompleta
        if current_sequence:
            sequences.append(current_sequence)
            print(f"    ⏳ Sequência incompleta com {len(current_sequence)} trades (posição aberta)")
        
        winning_sequences = 0
        losing_sequences = 0
        
        print(f"\n📈 ANALISANDO {len(sequences)} SEQUÊNCIAS:")
        
        for i, sequence in enumerate(sequences):
            sequence_pnl = self._calculate_sequence_pnl(sequence)
            sequence_type = "VENCEDORA" if sequence_pnl > 0 else "PERDEDORA" if sequence_pnl < 0 else "NEUTRA"
            
            print(f"  Sequência {i+1}: {len(sequence)} trades, PNL: ${sequence_pnl:.2f} ({sequence_type})")
            
            if sequence_pnl > 0:
                winning_sequences += 1
            elif sequence_pnl < 0:
                losing_sequences += 1
        
        return {
            "winning_trades": winning_sequences,
            "losing_trades": losing_sequences,
            "total_sequences": len(sequences),
            "sequences_detail": sequences
        }
    
    def _calculate_sequence_pnl(self, sequence: List) -> float:
        """
        Calcula o PNL de uma sequência de trades
        Considera: preço médio de entrada vs preço de saída
        """
        if not sequence:
            return 0.0
        
        # Separar trades por tipo
        entries = []
        exits = []
        
        for trade in sequence:
            if trade.trade_type in ["CLOSE", "REDUCE"]:
                exits.append(trade)
            elif trade.trade_type in ["BUY", "SELL", "DCA"]:
                entries.append(trade)
            else:
                entries.append(trade)
        
        if not entries:
            return 0.0
        
        # Calcular preço médio de entrada (weighted average)
        total_entry_value = sum(t.quantity * t.price for t in entries)
        total_entry_quantity = sum(t.quantity for t in entries)
        
        if total_entry_quantity == 0:
            return 0.0
        
        avg_entry_price = total_entry_value / total_entry_quantity
        
        # Se não há saídas, não há PNL realizado (posição ainda aberta)
        if not exits:
            return 0.0
        
        # Calcular PNL das saídas
        total_pnl = 0.0
        side = entries[0].side  # Assumir que toda sequência é do mesmo lado
        
        for exit_trade in exits:
            if side == "LONG":
                pnl = exit_trade.quantity * (exit_trade.price - avg_entry_price)
            else:  # SHORT
                pnl = exit_trade.quantity * (avg_entry_price - exit_trade.price)
            
            total_pnl += pnl
        
        return total_pnl