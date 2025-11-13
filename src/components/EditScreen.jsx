// Edit Screen Component
const EditScreen = ({ narrative, onContinue }) => {
  const [editedNarrative, setEditedNarrative] = React.useState(narrative || '');
  const [tone, setTone] = React.useState('');

  React.useEffect(() => {
    setEditedNarrative(narrative || '');
  }, [narrative]);

  const handleContinue = () => {
    if (!editedNarrative.trim()) {
      alert('Please enter a narrative for your case study');
      return;
    }
    onContinue(editedNarrative, tone);
  };

  return (
    <div className="edit-screen">
      <main className="edit-content">
        <div className="narrative-wrapper">
          <h1 className="review-title">Review outline</h1>
          <p className="review-subtitle">Here is your case study's narrative.</p>
          <textarea 
            className="narrative-textarea"
            value={editedNarrative}
            onChange={(e) => setEditedNarrative(e.target.value)}
            placeholder="Enter the narrative for your case study here..."
          />
        </div>
      </main>
      
      <footer className="edit-controls">
        <div className="control-group">
          <label className="control-label" htmlFor="tone-select">Tone</label>
          <select 
            id="tone-select" 
            className="control-select"
            value={tone}
            onChange={(e) => setTone(e.target.value)}
          >
            <option value="">Default</option>
            <option value="Professional">Professional</option>
            <option value="Conversational">Conversational</option>
            <option value="Academic">Academic</option>
            <option value="Creative">Creative</option>
            <option value="Technical">Technical</option>
          </select>
        </div>
        <button 
          className="continue-button" 
          onClick={handleContinue}
        >
          Continue
        </button>
      </footer>
    </div>
  );
};

