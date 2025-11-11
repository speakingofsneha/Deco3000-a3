## mvp 
- [x] parse from pdf 
- [x] chunk  
- [x] retrieve with provenance 
- [x] RAG-generate outline as outline.json 
- [x] map .json content onto slide template 
  - [x] needs to know when to add placeholder images 
- [x] png
  - [x] svg export or editing text in slides


## model/ pipeline
- [ ] the actual content generated is still kinda shit: 
  - [x] very little content is generated and that is also repetitive 
  - [x] still in bullet points instead of para 
  - [x] output should be inside output folder (both .json & .html) 
    - [x] use template as guide & parse infor inside it based on what it says.
  - [ ] very convuluded 'ai-esuqe' language, needs to be clearer, simpler & more natural. 
  - [ ] content is repetitve 
  - [ ] even with gaurdrails there is hallucination sometimes 
    - [ ] not sure if provenance even works properly
 - [x] body text & heading still dont always match sometimes 
- [ ] remove api nonsense ???


## design 
- [x] light & dark mode for slides 
- [x] slides template (diff layouts)
  - [x] no of points 
  - [x] media + description 
- [x] interface for application 
- [x] add favicon
- [ ] inbetween wf to edit narrative 


## bugs/ improvements
- [ ] laptop heats up soooo much sometimes (is it a memory or cpu issue?)
- [x] in deck.html, provencance is loaded in overline
- [ ] fix svg export
  - [x] headings are bold and italic when exported as svg and imported into figma 
  - [ ] layout itself is different and all text is on top of each other 
- [ ] improve project structure 


## documentation
- [ ] finish readme
- [ ] make changelog
- [ ] comment code!! <- do last