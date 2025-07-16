import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Home, RefreshCw } from "lucide-react";
import EyeBall from "@/components/EyeBall";

export default function ErrorPage({ 
  code, 
  title, 
  message, 
  showRetry = false, 
  onRetry,
  showHome = true 
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  let displayTitle = title;
  let displayMessage = message;
  
  // Get error data from translations based on code
  if (!displayTitle || !displayMessage) {
    let errorKey = null;
    
    // Map status codes to translation keys
    switch (code) {
      case 401:
        errorKey = '401';
        break;
      case 403:
        errorKey = '403';
        break;
      case 404:
        errorKey = '404';
        break;
      case 429:
        errorKey = '429';
        break;
      case 500:
        errorKey = '500';
        break;
      default:
        errorKey = null;
    }
    
    if (errorKey) {
      const errorData = t(`errors.${errorKey}`, { returnObjects: true });
      
      if (typeof errorData === 'object' && errorData.title && errorData.message) {
        if (!displayTitle) displayTitle = errorData.title;
        if (!displayMessage) displayMessage = errorData.message;
      }
    }
    
    // Final fallbacks
    if (!displayTitle) {
      displayTitle = code ? `Error ${code}` : 'Error';
    }
    
    if (!displayMessage) {
      displayMessage = 'Something went wrong. Please try again.';
    }
  }

  // 渲染錯誤碼，將 0 替換為眼球
  const renderErrorCode = (errorCode) => {
    if (!errorCode) return "ERROR";
    
    const codeString = errorCode.toString();
    return codeString.split('').map((char, index) => {
      if (char === '0') {
        return <EyeBall key={index} size="text-6xl md:text-9xl" />;
      }
      return (
        <span key={index} className="text-6xl md:text-9xl font-bold text-muted-foreground">
          {char}
        </span>
      );
    });
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4">
      <div className="text-center space-y-6 max-w-md">
        {/* Error Code with Eye Balls */}
        <h1 className="flex items-center justify-center">
          {renderErrorCode(code)}
        </h1>
        
        {/* Title */}
        <h2 className="text-2xl md:text-3xl font-semibold">
          {displayTitle}
        </h2>
        
        {/* Message */}
        <p className="text-muted-foreground text-base md:text-lg">
          {displayMessage}
        </p>
        
        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center items-center pt-4">
          {showRetry && onRetry && (
            <Button 
              onClick={onRetry}
              variant="default"
              className="w-full sm:w-auto"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              {t("common.retry")}
            </Button>
          )}
          
          {showHome && (
            <Button 
              onClick={() => navigate("/")}
              variant={showRetry ? "outline" : "default"}
              className="w-full sm:w-auto"
            >
              <Home className="w-4 h-4 mr-2" />
              {t("common.backHome")}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}