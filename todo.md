## functionality
- [ ] react app
- [ ] remove cli
- [x] pdf → chunks → outline (8 sections) → edited outline → final case study


## model/ pipeline
- [x] the actual content generated is still kinda shit: 
  - [x] very little content is generated and that is also repetitive 
  - [x] still in bullet points instead of para 
  - [x] output should be inside output folder (both .json & .html) 
    - [x] use template as guide & parse infor inside it based on what it says.
  - [x] body text & heading still dont always match sometimes 
- [x] outline before content generation
  - [x] very convuluded 'ai-esuqe' language, needs to be clearer, simpler & more natural. 
  - [x] content is very repetitve 
  - [x] even with gaurdrails there is SOO much hallucination 
- [ ] case study text does not intellilgently expand on the edited narrative  

## design 
- [x] light & dark mode for slides 
- [x] slides template (diff layouts)
  - [x] no of points 
  - [x] media + description 
- [x] interface for application 
- [x] scss instead of css
- [ ] improve slides ui
  - [ ] add img + text layout options
  - [ ] maybe some arc style gradient bg with noise instead of just black and white?
- [ ] improve deck
  - [ ] background button, export button 
  - [ ] title crumb overlapping with hamburger menu. 


## bugs/ improvements
- [ ] laptop heats up soooo much sometimes (is it a memory or cpu issue?)
- [ ] fix svg export (png?)
- [x] improve project structure 
- [x] onboarding


## documentation
- [ ] finish readme
- [ ] make changelog
  - [x] skeleton 
  - [ ] content
- [ ] comment code!!


## mvp (for proof of concept)
- [x] parse from pdf 
- [x] chunk  
- [x] retrieve with provenance 
- [x] RAG-generate outline as outline.json 
- [x] map .json content onto slide template 
  - [x] needs to know when to add placeholder images 
- [x] png
  - [x] svg export or editing text in slides
