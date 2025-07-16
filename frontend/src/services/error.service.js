import i18n from '@/i18n';

// Get error message with i18n support - updated for new format
const getErrorMessage = (key) => {
  const errorData = i18n.t(`errors.${key}`, { returnObjects: true });
  
  // If it's an object with title and message, return the message
  if (typeof errorData === 'object' && errorData.message) {
    return errorData.message;
  }
  
  // Fallback for old format or missing translations
  return typeof errorData === 'string' ? errorData : 'An error occurred';
};

// Get error title with i18n support
const getErrorTitle = (key) => {
  const errorData = i18n.t(`errors.${key}`, { returnObjects: true });
  
  // If it's an object with title and message, return the title
  if (typeof errorData === 'object' && errorData.title) {
    return errorData.title;
  }
  
  // Fallback for old format or missing translations
  return 'Error';
};

// Get complete error data (title and message)
const getErrorData = (key) => {
  const errorData = i18n.t(`errors.${key}`, { returnObjects: true });
  
  if (typeof errorData === 'object' && errorData.title && errorData.message) {
    return errorData;
  }
  
  // Fallback for old format
  return {
    title: 'Error',
    message: typeof errorData === 'string' ? errorData : 'An error occurred'
  };
};

// Global error handler function (can be set by app to show notifications)
let showErrorFunction = null;

// Set error display function
export const setErrorHandler = (showError) => {
  showErrorFunction = showError;
};

// Helper function to show error (fallback if no error handler is set)
export const showError = (message) => {
  if (showErrorFunction) {
    showErrorFunction(message);
  } else {
    // Fallback to console if no error handler is set
    console.warn('No error handler set. Error message:', message);
  }
};

// Main error handling function
export const handleApiError = (error, logoutFunction) => {
  const status = error.response?.status;
  const method = error.config?.method?.toUpperCase();
  const url = error.config?.url;
  
  console.error(`API Error: ${status || 'Network'} ${method} ${url}`);
  
  // Handle specific status codes
  switch (status) {
    case 401:
      console.error('401 - Invalid or expired token');
      showError(getErrorMessage('401'));
      break;
      
    case 403:
      console.error('403 - Permission denied');
      showError(getErrorMessage('403'));
      break;
      
    case 429:
      console.error('429 - Too many failed attempts. Try again later.');
      showError(getErrorMessage('429'));
      break;
      
    case 500:
      console.error('500 Internal Server Error');
      showError(getErrorMessage('500'));
      break;
      
    default:
      // Network error or other status codes
      if (!status) {
        console.error('Network error - no response from server');
        showError(getErrorMessage('network'));
      } else {
        console.error(`Unhandled status code: ${status}`);
        showError('An unexpected error occurred');
      }
  }
};

// Export helper functions
export { getErrorMessage, getErrorTitle, getErrorData };

// Export for backward compatibility
export default {
  setErrorHandler,
  handleApiError,
  showError,
  getErrorMessage,
  getErrorTitle,
  getErrorData
}; 