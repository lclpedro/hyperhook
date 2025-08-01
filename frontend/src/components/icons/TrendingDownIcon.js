import React from 'react';

const TrendingDownIcon = ({ size = 20, color = 'currentColor', ...props }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke={color}
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <polyline points="22,17 13.5,8.5 8.5,13.5 2,7"></polyline>
    <polyline points="16,17 22,17 22,11"></polyline>
  </svg>
);

export default TrendingDownIcon;