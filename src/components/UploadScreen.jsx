// Upload Screen Component
const UploadScreen = ({ onFileSelected, onReframe }) => {
  const [selectedFile, setSelectedFile] = React.useState(null);
  const [error, setError] = React.useState('');
  const fileInputRef = React.useRef(null);
  const uploadAreaRef = React.useRef(null);

  const handleFileSelection = (file) => {
    if (file.type !== 'application/pdf') {
      setError('Please select a PDF file');
      return;
    }
    setSelectedFile(file);
    setError('');
    onFileSelected(file);
  };

  const handleFileInput = (e) => {
    const file = e.target.files[0];
    if (file) handleFileSelection(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    uploadAreaRef.current?.classList.add('dragover');
  };

  const handleDragLeave = () => {
    uploadAreaRef.current?.classList.remove('dragover');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    uploadAreaRef.current?.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
      handleFileSelection(file);
      if (fileInputRef.current) {
        fileInputRef.current.files = e.dataTransfer.files;
      }
    } else {
      setError('Please upload a PDF file');
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="upload-screen">
      <main className="upload-content">
        <h1 className="upload-title">Welcome to Reframe</h1>
        <p className="upload-subtitle">How would you like to get started?</p>
        
        <div 
          className="upload-area"
          ref={uploadAreaRef}
          onClick={handleClick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="upload-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 4V20M12 4L8 8M12 4L16 8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <label htmlFor="file-input" className="upload-label">Import Content</label>
          <p className="upload-description">Turn your pdf an engaging case study</p>
          <input 
            type="file" 
            id="file-input" 
            className="upload-input" 
            accept=".pdf"
            ref={fileInputRef}
            onChange={handleFileInput}
          />
        </div>
        
        <button 
          className="reframe-button" 
          onClick={onReframe}
          disabled={!selectedFile}
        >
          Reframe it
        </button>
        {error && <div className="error-message">{error}</div>}
      </main>
    </div>
  );
};

