## mvp 
- [x] parse from pdf 
- [x] chunk  
- [x] retrieve with provenance 
- [x] RAG-generate outline as outline.json 
- [x] map .json content onto slide template 
  - [ ] intelligently add placeholder images
- [x] png
  - [ ] svg export or editing text in slides


## model/ pipeline
- [ ] the actual content generated is still pretty shit: 
    - [ ] very little content is generated (should be around 400-600 words) and that is also repetitive 
    - [ ] still in bullet points instead of para 
    - [x] output should be inside output folder (both .json & .html) 
        - [x] use template as guide & parse infor inside it based on what it says.
 - [ ] very convuluded 'ai-esuqe' language, needs to be clearer, simpler & more natural. 
 - [ ] not sure if we need provenance (since content is short, it is easy to check if content is hallucinated or not) 
 - [ ] needs to know when to add placeholder images 
 - [ ] remove api nonsense 
 - [ ] body text & heading still dont match sometimes 


## design 
- [ ] slides template (diff layouts)
- [ ] interface for application 


## bugs/ improvements
- [ ] laptop heats up soooo much sometimes (is it a memory or cpu issue?)
- [ ] in deck.html, provencance is loaded in overline


## documentation
- [ ] finish readme
- [ ] make changelog
- [ ] comment code!! <- do last