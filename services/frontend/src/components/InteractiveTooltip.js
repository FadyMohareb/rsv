/**
 * @module InteractiveTooltip
 * 
 * @description Interactive tooltip to help understand inputs and other items.
 * @returns {JSX.Element} The rendered tooltip span.
 */
import React, { useState } from 'react';

const InteractiveTooltip = ({ tooltipText }) => {
  const [visible, setVisible] = useState(false);

  return (
    <span 
      className="info-icon"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      ?
      {visible && <span className="tooltip">{tooltipText}</span>}
    </span>
  );
};

export default InteractiveTooltip;