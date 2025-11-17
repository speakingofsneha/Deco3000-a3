// edit screen component
const EditScreen = ({ narrative, onContinue }) => {
  const [editedNarrative, setEditedNarrative] = React.useState(narrative || '');
  const [isDisclaimerExpanded, setIsDisclaimerExpanded] = React.useState(true);
  const textareaRef = React.useRef(null);

  // update the textarea when narrative prop changes
  React.useEffect(() => {
    setEditedNarrative(narrative || '');
    if (textareaRef.current) {
      if (narrative) {
        textareaRef.current.textContent = narrative;
        // format after setting content
        setTimeout(() => {
          formatTextareaContent();
        }, 10);
      } else {
        textareaRef.current.textContent = '';
      }
    }
  }, [narrative]);

  // format markdown-style text to html (**text** = bold, [text] = italic)
  const formatTextareaContent = () => {
    if (!textareaRef.current) return;
    
    const element = textareaRef.current;
    const text = element.textContent || element.innerText || '';
    
    // save cursor position before formatting
    const selection = window.getSelection();
    const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
    const cursorPosition = range ? range.startOffset : 0;
    
    // convert markdown to html
    let formattedHtml = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\[(.*?)\]/g, '<em>$1</em>');
    
    element.innerHTML = formattedHtml;
    
    // try to restore cursor position after formatting
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
        // ignore cursor restoration errors
      }
    }
  };

  // handle typing in the textarea
  const handleInput = (e) => {
    const text = e.target.textContent || e.target.innerText || '';
    setEditedNarrative(text);
    
    // format after a short delay so typing feels smooth
    setTimeout(() => {
      formatTextareaContent();
    }, 50);
  };

  // handle paste events, strip formatting and insert plain text
  const handlePaste = (e) => {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text/plain');
    document.execCommand('insertText', false, text);
    setTimeout(() => {
      formatTextareaContent();
    }, 10);
  };

  // validate and continue to next step
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
          {/* collapsible disclaimer card */}
          <div className="disclaimer-container">
            <div className={`disclaimer-card ${isDisclaimerExpanded ? 'expanded' : 'collapsed'}`}>
              <div className="disclaimer-icon">i</div>
              <div className="disclaimer-copy">
                {/* clickable header to expand/collapse */}
                <div 
                  className="disclaimer-header"
                  onClick={() => setIsDisclaimerExpanded(!isDisclaimerExpanded)}
                  style={{ cursor: 'pointer' }}
                >
                  <p className="disclaimer-heading">Disclaimer</p>
                  <span className={`disclaimer-arrow ${isDisclaimerExpanded ? 'expanded' : ''}`}>▼</span>
                </div>
                {isDisclaimerExpanded && (
                  <p className="disclaimer-text">{disclaimerText}</p>
                )}
              </div>
            </div>
          </div>
          {/* editable textarea with markdown formatting */}
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
            <button 
              className="continue-button" 
              onClick={handleContinue}
            >
              Continue
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};