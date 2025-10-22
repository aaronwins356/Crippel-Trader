import React, { useState, useRef, useEffect } from 'react';
import MatrixRain from './MatrixRain';
import ChatInterface from './ChatInterface';

const App = () => {
  const [isBooted, setIsBooted] = useState(false);

  useEffect(() => {
    // Simulate terminal boot sequence
    const bootSequence = setTimeout(() => {
      setIsBooted(true);
    }, 3000);

    return () => clearTimeout(bootSequence);
  }, []);

  return (
    <div className="app-container">
      <MatrixRain />
      
      {!isBooted ? (
        <div className="boot-screen">
          <div className="boot-text">
            <div className="line">INITIALIZING MATRIX NODE...</div>
            <div className="line">LOADING CORE MODULES...</div>
            <div className="line">ESTABLISHING CONNECTION TO LOCAL LLM...</div>
            <div className="line">READY.</div>
            <div className="cursor"></div>
          </div>
        </div>
      ) : (
        <ChatInterface />
      )}
    </div>
  );
};

export default App;