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
        <h1 className="upload-title">Upload your visual report</h1>
        <p className="upload-subtitle">We’ll turn it into an engaging case study ;)</p>
        
        <div className="upload-card">
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
                <path d="M12 4V20M12 4L8 8M12 4L16 8" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <label htmlFor="file-input" className="upload-label">Drop your PDF here or browse</label>
            <p className="upload-description">Max file size up to 1 GB</p>
            <input 
              type="file" 
              id="file-input" 
              className="upload-input" 
              accept=".pdf"
              ref={fileInputRef}
              onChange={handleFileInput}
            />
          </div>

          {selectedFile && (
            <div className="upload-list">
              <div className="upload-item">
                <div className="upload-item-icon">PDF</div>
                <div className="upload-item-details">
                  <p className="upload-item-name">{selectedFile.name}</p>
                  <p className="upload-item-size">{(selectedFile.size / (1024 * 1024)).toFixed(1)} MB</p>
                </div>
                <button 
                  className="upload-item-remove"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                    setError('');
                    if (fileInputRef.current) {
                      fileInputRef.current.value = '';
                    }
                  }}
                  aria-label="Remove file"
                >
                  ✕
                </button>
              </div>
            </div>
          )}
          
          {error && <div className="error-message">{error}</div>}
        </div>
        
        <button 
          className="upload-button primary" 
          onClick={onReframe}
          disabled={!selectedFile}
        >
          Reframe it
        </button>
      </main>
    </div>
  );
};

