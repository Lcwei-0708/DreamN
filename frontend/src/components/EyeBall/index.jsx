import { useState, useEffect, useRef } from 'react';

const EyeBall = ({ size = 'text-6xl md:text-9xl' }) => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const eyeRef = useRef(null);

  useEffect(() => {
    const handleMouseMove = (e) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const calculateEyeMovement = () => {
    if (!eyeRef.current) return { x: 0, y: 0 };

    const eyeRect = eyeRef.current.getBoundingClientRect();
    const eyeCenterX = eyeRect.left + eyeRect.width / 2;
    const eyeCenterY = eyeRect.top + eyeRect.height / 2;

    const angle = Math.atan2(mousePosition.y - eyeCenterY, mousePosition.x - eyeCenterX);
    const distance = Math.min(eyeRect.width * 0.15, eyeRect.height * 0.15);

    return {
      x: Math.cos(angle) * distance,
      y: Math.sin(angle) * distance
    };
  };

  const { x, y } = calculateEyeMovement();

  return (
    <div 
      ref={eyeRef}
      className={`inline-block relative ${size} font-bold text-muted-foreground`}
      style={{ 
        width: '1em', 
        height: '1.2em',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      {/* eyeball frame */}
      <div 
        className="absolute rounded-full bg-white border-4 border-muted-foreground"
        style={{
          width: '0.8em',
          height: '0.8em',
        }}
      >
        {/* eyeball */}
        <div
          className="absolute rounded-full bg-black transition-transform duration-100 ease-out"
          style={{
            width: '0.3em',
            height: '0.3em',
            top: '50%',
            left: '50%',
            transform: `translate(-50%, -50%) translate(${x}px, ${y}px)`,
          }}
        />
      </div>
    </div>
  );
};

export default EyeBall;