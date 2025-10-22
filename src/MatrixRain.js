import React, { useEffect, useRef } from 'react';

const MatrixRain = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Set canvas dimensions
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();
    
    // Matrix characters
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$#@%&*";
    const charArray = chars.split("");
    
    // Raindrops
    const fontSize = 14;
    const columns = canvas.width / fontSize;
    
    // Create raindrops array
    const raindrops = [];
    for (let i = 0; i < columns; i++) {
      raindrops[i] = Math.floor(Math.random() * canvas.height / fontSize);
    }
    
    // Draw function
    const draw = () => {
      // Semi-transparent black overlay for trail effect
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      ctx.font = `${fontSize}px monospace`;
      
      for (let i = 0; i < raindrops.length; i++) {
        // Random character
        const char = charArray[Math.floor(Math.random() * charArray.length)];
        
        // Green text with varying intensity
        const greenIntensity = 150 + Math.floor(Math.random() * 105);
        ctx.fillStyle = `rgb(0, ${greenIntensity}, 0)`;
        
        // Draw character
        ctx.fillText(char, i * fontSize, raindrops[i] * fontSize);
        
        // Reset drop if it reaches bottom or randomly
        if (raindrops[i] * fontSize > canvas.height && Math.random() > 0.975) {
          raindrops[i] = 0;
        }
        
        raindrops[i]++;
      }
    };
    
    // Animation loop
    const interval = setInterval(draw, 50);
    
    return () => {
      clearInterval(interval);
      window.removeEventListener('resize', resizeCanvas);
    };
  }, []);

  return <canvas ref={canvasRef} className="matrix-canvas" />;
};

export default MatrixRain;