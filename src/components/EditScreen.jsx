// Edit Screen Component
const EditScreen = ({ narrative, onContinue }) => {
  const [editedNarrative, setEditedNarrative] = React.useState(narrative || '');
  const [isDisclaimerVisible, setIsDisclaimerVisible] = React.useState(true);
  const textareaRef = React.useRef(null);

  React.useEffect(() => {
    setEditedNarrative(narrative || '');
    if (textareaRef.current) {
      // Set the text content of the contentEditable div
      if (narrative) {
        textareaRef.current.textContent = narrative;
        // Format the content after setting it
        setTimeout(() => {
          formatTextareaContent();
        }, 10);
      } else {
        textareaRef.current.textContent = '';
      }
    }
  }, [narrative]);

  const formatTextareaContent = () => {
    if (!textareaRef.current) return;
    
    const element = textareaRef.current;
    const text = element.textContent || element.innerText || '';
    
    // Save cursor position
    const selection = window.getSelection();
    const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
    const cursorPosition = range ? range.startOffset : 0;
    
    // Format the text: **text** becomes bold, [text] becomes italic
    let formattedHtml = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\[(.*?)\]/g, '<em>$1</em>');
    
    element.innerHTML = formattedHtml;
    
    // Restore cursor position if possible
    if (range && element.firstChild) {
      try {
        const newRange = document.createRange();
        const textNode = element.firstChild;
        const offset = Math.min(cursorPosition, textNode.textContent.length);
        newRange.setStart(textNode, offset);
        newRange.setEnd(textNode, offset);
        selection.removeAllRanges();
        selection.addRange(newRange);
      } catch (e) {
        // Ignore cursor restoration errors
      }
    }
  };

  const handleInput = (e) => {
    const text = e.target.textContent || e.target.innerText || '';
    setEditedNarrative(text);
    
    // Format after a short delay to allow typing
    setTimeout(() => {
      formatTextareaContent();
    }, 50);
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text/plain');
    document.execCommand('insertText', false, text);
    setTimeout(() => {
      formatTextareaContent();
    }, 10);
  };

  const handleContinue = () => {
    if (!editedNarrative.trim()) {
      alert('Please generate a narrative');
      return;
    }
    onContinue(editedNarrative);
  };

  const disclaimerText = "I generated this outline by analysing the text in your report, but i don't actually know your lived experience, your intentions, or what really happened in your project. I make my best guess based on patterns in the writing you provided, so please double-check that my interpretations truly reflect your process. The quality of what i produce depends on the effort you put in. if your edits are minimal and vague so will your case study :( Refining your narrative here helps me generate a much stronger case study later, so always review, edit and make it yours!";

  return (
    <div className="edit-screen">
      <main className="edit-content">
        <div className="narrative-wrapper">
          <h1 className="review-title">Review outline</h1>
          <div className="disclaimer-container">
            {isDisclaimerVisible ? (
              <div className="disclaimer-card">
                <div className="disclaimer-icon">i</div>
                <div className="disclaimer-copy">
                  <p className="disclaimer-heading">Dis</p>
                  <p className="disclaimer-text">{disclaimerText}</p>
                </div>
                <button 
                  className="disclaimer-close"
                  onClick={() => setIsDisclaimerVisible(false)}
                  aria-label="Dismiss disclaimer"
                >
                  ✕
                </button>
              </div>
            ) : (
              <button 
                className="disclaimer-show"
                onClick={() => setIsDisclaimerVisible(true)}
              >
                Show disclaimer
              </button>
            )}
          </div>
          <div className="textarea-container">
            <div
              ref={textareaRef}
              className="narrative-textarea"
              contentEditable
              onInput={handleInput}
              onPaste={handlePaste}
              data-placeholder="Generate a narrative for your case study here..."
              suppressContentEditableWarning={true}
            />
          </div>
          <button 
            className="continue-button" 
            onClick={handleContinue}
          >
            Continue
          </button>
        </div>
      </main>
    </div>
  );
};