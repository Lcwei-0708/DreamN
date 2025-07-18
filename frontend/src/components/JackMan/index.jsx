import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import classes from './index.module.scss';
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
        className={classes.jackManBox}
        style={{
          width: `${size}px`,
          height: `${size}px`,
        }}
      >
        <div className={classes.loading}>
          <Loader2 className="w-5 h-5 animate-spin" />
        </div>
        {/* Hidden images for loading */}
        <img 
          ref={jackManRef}
          src={jackMan} 
          alt="jackMan"
          onLoad={() => handleImageLoad('jackMan')}
          style={{ display: 'none' }}
        />
        <img
          ref={jackMaskRef}
          src={jackMask}
          alt="jackMask"
          onLoad={() => handleImageLoad('jackMask')}
          style={{ display: 'none' }}
        />
      </div>
    );
  }

  return (
    <div 
      className={classes.jackManBox} 
      ref={containerRef}
      style={{
        width: `${size}px`,
        height: `${size}px`,
      }}
    >
      <div 
        className={classes.jackMan} 
        style={{
          backgroundImage: `url(${jackMan})`,
          backgroundSize: 'contain',
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'center'
        }}
      />
      <motion.div
        className={classes.jackMask}
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
              className={classes.eyeGlow}
              style={{
                left: `calc(50% + ${leftEyeX}px)`,
                top: `calc(50% + ${leftEyeY}px)`,
              }}
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: scaleRatio }}
              exit={{ opacity: 0, scale: 0.5 }}
              transition={{ duration: 0.2 }}
            >
              <div className={classes.eyeCore}></div>
              <div className={classes.eyeRing}></div>
              <div className={classes.eyeFlare}></div>
            </motion.div>
            
            {/* Right eye glow effect */}
            <motion.div
              className={classes.eyeGlow}
              style={{
                left: `calc(50% + ${rightEyeX}px)`,
                top: `calc(50% + ${rightEyeY}px)`,
              }}
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: scaleRatio }}
              exit={{ opacity: 0, scale: 0.5 }}
              transition={{ duration: 0.2 }}
            >
              <div className={classes.eyeCore}></div>
              <div className={classes.eyeRing}></div>
              <div className={classes.eyeFlare}></div>
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
              className={classes.laserBeam}
              style={{
                left: `calc(50% + ${leftEyeX}px)`,
                top: `calc(50% + ${leftEyeY}px)`,
                transform: `rotate(${leftBeamProps.angle}deg)`,
                transformOrigin: '0 50%',
                height: `${7 * scaleRatio}px`,
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
            />
            
            {/* Right eye laser beam */}
            <motion.div
              className={classes.laserBeam}
              style={{
                left: `calc(50% + ${rightEyeX}px)`,
                top: `calc(50% + ${rightEyeY}px)`,
                transform: `rotate(${rightBeamProps.angle}deg)`,
                transformOrigin: '0 50%',
                height: `${7 * scaleRatio}px`,
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
            />
          </>
        )}
      </AnimatePresence>
      
      <div 
        className={classes.actBtn} 
        onClick={handleButtonClick}
        style={{
          left: '35.7%',
          top: '48.5%',
          width: `${30 * scaleRatio}px`,
          height: `${30 * scaleRatio}px`,
        }}
      />
    </div>
  );
};

export default JackMan;