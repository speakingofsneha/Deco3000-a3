// Loading Screen Component
const LoadingScreen = ({ message = 'Processing your document' }) => {
  return (
    <div className="loading-screen">
      <div className="loading-content">
        <div className="loading-spinner"></div>
        <h2 className="loading-title">Processing your document</h2>
        <p className="loading-message">{message}</p>
      </div>
    </div>
  );
};

