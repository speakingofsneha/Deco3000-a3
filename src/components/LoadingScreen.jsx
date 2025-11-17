// loading screen component
const LoadingScreen = ({ title = 'Generating outline', message = '' }) => {
  return (
    <div className="loading-screen">
      <div className="loading-content">
        {/* animated spinner */}
        <div className="loading-spinner"></div>
        {title && <h2 className="loading-title">{title}</h2>}
      </div>
    </div>
  );
};

