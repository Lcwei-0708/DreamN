import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import jackMan from './Jack.png';
import jackMask from './mask.png';

const JackMan = ({ size = 300 }) => {
  const [maskRotation, setMaskRotation] = useState(0);
  const [imagesLoaded, setImagesLoaded] = useState({
    jackMan: false,
    jackMask: false
  });
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isMouseDown, setIsMouseDown] = useState(false);
  const [showEyeGlow, setShowEyeGlow] = useState(false);
  const [showLaser, setShowLaser] = useState(false);
  
  const jackManRef = useRef(null);
  const jackMaskRef = useRef(null);
  const containerRef = useRef(null);
  const laserTimeoutRef = useRef(null);

  // Calculate scale ratio based on size
  const scaleRatio = size / 300;

  // Check if all images are loaded
  const allImagesLoaded = Object.values(imagesLoaded).every(loaded => loaded);

  const handleImageLoad = (imageName) => {
    setImagesLoaded(prev => ({
      ...prev,
      [imageName]: true
    }));
  };

  // Check if images are already loaded (cached)
  useEffect(() => {
    const checkImageLoad = (imgRef, imageName) => {
      if (imgRef.current && imgRef.current.complete) {
        handleImageLoad(imageName);
      }
    };

    checkImageLoad(jackManRef, 'jackMan');
    checkImageLoad(jackMaskRef, 'jackMask');
  }, []);

  // Track mouse movement and mouse events
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setMousePosition({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        });
      }
    };

    const handleMouseDown = () => {
      if (maskRotation > 0) {
        setIsMouseDown(true);
        setShowEyeGlow(true);
        
        // Clear previous timeout
        if (laserTimeoutRef.current) {
          clearTimeout(laserTimeoutRef.current);
        }
        
        // Delay showing laser
        laserTimeoutRef.current = setTimeout(() => {
          setShowLaser(true);
        }, 100);
      }
    };

    const handleMouseUp = () => {
      // Clear timeout to prevent delayed laser display
      if (laserTimeoutRef.current) {
        clearTimeout(laserTimeoutRef.current);
        laserTimeoutRef.current = null;
      }
      
      setIsMouseDown(false);
      setShowEyeGlow(false);
      setShowLaser(false);
    };

    if (maskRotation > 0) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mousedown', handleMouseDown);
      document.addEventListener('mouseup', handleMouseUp);
      // Add global mouse release event to handle mouse release outside window
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('mouseup', handleMouseUp);
      
      // Cleanup timeout
      if (laserTimeoutRef.current) {
        clearTimeout(laserTimeoutRef.current);
      }
    };
  }, [maskRotation]); // Remove isMouseDown dependency

  const handleButtonClick = () => {
    // Clear all related states and timeout
    if (laserTimeoutRef.current) {
      clearTimeout(laserTimeoutRef.current);
      laserTimeoutRef.current = null;
    }
    
    setMaskRotation(prev => prev === 0 ? 10 : 0);
    setIsMouseDown(false);
    setShowEyeGlow(false);
    setShowLaser(false);
  };

  // Add additional useEffect to monitor maskRotation changes
  useEffect(() => {
    if (maskRotation === 0) {
      // Force clear all laser-related states when mask is closed
      if (laserTimeoutRef.current) {
        clearTimeout(laserTimeoutRef.current);
        laserTimeoutRef.current = null;
      }
      setIsMouseDown(false);
      setShowEyeGlow(false);
      setShowLaser(false);
    }
  }, [maskRotation]);

  // Calculate opacity
  const opacity = 1 - (maskRotation / 10);

  // Calculate laser beam properties
  const calculateBeamProperties = (eyeX, eyeY) => {
    if (!containerRef.current) return { angle: 0, length: 0 };
    
    const rect = containerRef.current.getBoundingClientRect();
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    
    const actualEyeX = centerX + eyeX;
    const actualEyeY = centerY + eyeY;
    
    const deltaX = mousePosition.x - actualEyeX;
    const deltaY = mousePosition.y - actualEyeY;
    
    const angle = Math.atan2(deltaY, deltaX) * (180 / Math.PI);
    const length = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    
    return { angle, length };
  };

  // Eye positions relative to center (scaled based on size)
  const leftEyeX = -45 * scaleRatio;
  const leftEyeY = -58 * scaleRatio;
  const rightEyeX = -7 * scaleRatio;
  const rightEyeY = -58 * scaleRatio;

  const leftBeamProps = calculateBeamProperties(leftEyeX, leftEyeY);
  const rightBeamProps = calculateBeamProperties(rightEyeX, rightEyeY);

  const handleDragStart = (e) => {
    e.preventDefault();
    return false;
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    return false;
  };

  // Show loading state if images are not loaded
  if (!allImagesLoaded) {
    return (
      <div 
        className="relative w-[300px] aspect-square inline-block"
        style={{
          width: `${size}px`,
          height: `${size}px`,
        }}
      >
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 flex items-center justify-center z-10">
          <Loader2 className="w-5 h-5 animate-spin" />
        </div>
        {/* Hidden images for loading */}
        <img 
          ref={jackManRef}
          src={jackMan} 
          alt="jackMan"
          onLoad={() => handleImageLoad('jackMan')}
          className="hidden"
        />
        <img
          ref={jackMaskRef}
          src={jackMask}
          alt="jackMask"
          onLoad={() => handleImageLoad('jackMask')}
          className="hidden"
        />
      </div>
    );
  }

  return (
    <div 
      className="relative w-[300px] aspect-square inline-block" 
      ref={containerRef}
      style={{
        width: `${size}px`,
        height: `${size}px`,
      }}
    >
      <div 
        className="w-full h-full block select-none"
        style={{
          backgroundImage: `url(${jackMan})`,
          backgroundSize: 'contain',
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'center'
        }}
      />
      <motion.div
        className="absolute top-0 left-0 w-full h-full pointer-events-none select-none"
        style={{
          backgroundImage: `url(${jackMask})`,
          backgroundSize: 'contain',
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'center',
          transformOrigin: "top center"
        }}
        initial={{ rotateX: 0, y: 0, opacity: 1 }}
        animate={{
          rotateX: maskRotation,
          y: -maskRotation * scaleRatio,
          opacity: opacity
        }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
      />
      
      {/* Eye glow effect - Show first */}
      <AnimatePresence>
        {maskRotation > 0 && showEyeGlow && (
          <>
            {/* Left eye glow effect */}
            <motion.div
              className="absolute transform -translate-x-1/2 -translate-y-1/2 pointer-events-none z-6"
              style={{
                left: `calc(50% + ${leftEyeX}px)`,
                top: `calc(50% + ${leftEyeY}px)`,
              }}
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: scaleRatio }}
              exit={{ opacity: 0, scale: 0.5 }}
              transition={{ duration: 0.2 }}
            >
              <div className="absolute w-2 h-2 bg-gradient-radial from-white via-red-400 to-red-600 rounded-full transform -translate-x-1/2 -translate-y-1/2 animate-pulse shadow-lg shadow-red-500/80"></div>
              <div className="absolute w-5 h-5 border-2 border-red-500/60 rounded-full transform -translate-x-1/2 -translate-y-1/2 animate-ping shadow-lg shadow-red-500/40"></div>
              <div className="absolute w-8 h-8 bg-gradient-radial from-red-500/30 via-red-500/10 to-transparent rounded-full transform -translate-x-1/2 -translate-y-1/2 animate-pulse">
                <div className="absolute top-1/2 left-1/2 w-10 h-0.5 bg-gradient-to-r from-transparent via-red-500/80 to-transparent transform -translate-x-1/2 -translate-y-1/2 shadow-lg shadow-red-500/60"></div>
                <div className="absolute top-1/2 left-1/2 w-0.5 h-10 bg-gradient-to-b from-transparent via-red-500/80 to-transparent transform -translate-x-1/2 -translate-y-1/2 shadow-lg shadow-red-500/60"></div>
              </div>
            </motion.div>
            
            {/* Right eye glow effect */}
            <motion.div
              className="absolute transform -translate-x-1/2 -translate-y-1/2 pointer-events-none z-6"
              style={{
                left: `calc(50% + ${rightEyeX}px)`,
                top: `calc(50% + ${rightEyeY}px)`,
              }}
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: scaleRatio }}
              exit={{ opacity: 0, scale: 0.5 }}
              transition={{ duration: 0.2 }}
            >
              <div className="absolute w-2 h-2 bg-gradient-radial from-white via-red-400 to-red-600 rounded-full transform -translate-x-1/2 -translate-y-1/2 animate-pulse shadow-lg shadow-red-500/80"></div>
              <div className="absolute w-5 h-5 border-2 border-red-500/60 rounded-full transform -translate-x-1/2 -translate-y-1/2 animate-ping shadow-lg shadow-red-500/40"></div>
              <div className="absolute w-8 h-8 bg-gradient-radial from-red-500/30 via-red-500/10 to-transparent rounded-full transform -translate-x-1/2 -translate-y-1/2 animate-pulse">
                <div className="absolute top-1/2 left-1/2 w-10 h-0.5 bg-gradient-to-r from-transparent via-red-500/80 to-transparent transform -translate-x-1/2 -translate-y-1/2 shadow-lg shadow-red-500/60"></div>
                <div className="absolute top-1/2 left-1/2 w-0.5 h-10 bg-gradient-to-b from-transparent via-red-500/80 to-transparent transform -translate-x-1/2 -translate-y-1/2 shadow-lg shadow-red-500/60"></div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Laser beam - Delayed display with expansion animation */}
      <AnimatePresence>
        {maskRotation > 0 && showLaser && (
          <>
            {/* Left eye laser beam */}
            <motion.div
              className="absolute rounded-full pointer-events-none z-5"
              style={{
                left: `calc(50% + ${leftEyeX}px)`,
                top: `calc(50% + ${leftEyeY}px)`,
                transform: `rotate(${leftBeamProps.angle}deg)`,
                transformOrigin: '0 50%',
                height: `${7 * scaleRatio}px`,
                background: 'linear-gradient(90deg, rgba(255, 0, 0, 0.9) 0%, rgba(255, 0, 0, 0.7) 30%, rgba(255, 0, 0, 0.3) 70%, transparent 100%)',
                boxShadow: '0 0 10px rgba(255, 0, 0, 0.8), 0 0 20px rgba(255, 0, 0, 0.6), 0 0 30px rgba(255, 0, 0, 0.4)',
                '--laser-inner-height': `${5 * scaleRatio}px`
              }}
              initial={{ width: 0, opacity: 0 }}
              animate={{ 
                width: `${leftBeamProps.length}px`, 
                opacity: 1 
              }}
              transition={{ 
                duration: 0.4, 
                ease: "easeOut",
                width: { duration: 0.6 }
              }}
            >
              <div 
                className="absolute top-1/2 left-0 w-full rounded-full bg-white/90 transform -translate-y-1/2"
                style={{ height: 'var(--laser-inner-height, 5px)' }}
              ></div>
            </motion.div>
            
            {/* Right eye laser beam */}
            <motion.div
              className="absolute rounded-full pointer-events-none z-5"
              style={{
                left: `calc(50% + ${rightEyeX}px)`,
                top: `calc(50% + ${rightEyeY}px)`,
                transform: `rotate(${rightBeamProps.angle}deg)`,
                transformOrigin: '0 50%',
                height: `${7 * scaleRatio}px`,
                background: 'linear-gradient(90deg, rgba(255, 0, 0, 0.9) 0%, rgba(255, 0, 0, 0.7) 30%, rgba(255, 0, 0, 0.3) 70%, transparent 100%)',
                boxShadow: '0 0 10px rgba(255, 0, 0, 0.8), 0 0 20px rgba(255, 0, 0, 0.6), 0 0 30px rgba(255, 0, 0, 0.4)',
                '--laser-inner-height': `${5 * scaleRatio}px`
              }}
              initial={{ width: 0, opacity: 0 }}
              animate={{ 
                width: `${rightBeamProps.length}px`, 
                opacity: 1 
              }}
              transition={{ 
                duration: 0.4, 
                ease: "easeOut",
                width: { duration: 0.6 }
              }}
            >
              <div 
                className="absolute top-1/2 left-0 w-full rounded-full bg-white/90 transform -translate-y-1/2"
                style={{ height: 'var(--laser-inner-height, 5px)' }}
              ></div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
      
      <div 
        className="absolute rounded-full bg-cover transition-shadow duration-200 cursor-pointer select-none z-2 hover:shadow-[0_0_15px_5px_#03e084,0_0_30px_10px_rgba(3,224,132,0.5)] hover:border-[#03e084] border-3 border-transparent"
        onClick={handleButtonClick}
        style={{
          left: '35.92%',
          top: '49.1%',
          width: `${26.85 * scaleRatio}px`,
          height: `${26.85 * scaleRatio}px`,
        }}
      />
    </div>
  );
};

export default JackMan;