Sono uno studente di Ingegneria Informatica all'Università di Bologna.
Vorrei dovermi preoccupare esclusivamente di studiare e per questo serve automatizzare alcuni processi.

## Processi

### Get, Parse, Move and Push
Al momento sono riuscito ad automatizzare il processo di download: 
l'insegnante pubblica su Virtuale (pagina web) i file relativi al corso da cui studiare.
Solo alcuni però sono davvero fondamentali, altri sono ridondanti come testi opzionali.
I testi utili poi li uso come contesto per NotebookLM 
e siccome le lezioni di Fisica e Matematica sono scritte a mano
allora li traduco in markdown.
Questa pipeline vuole automatizzare questo intero processo: `Download`, `Select`, `Convert` in markdown e `Upload` a NotebookLM

#### Get
La pagina di virtuale è strutturata per sezioni, come puoi vedere nella [pagina di matematica applicata](paina-matematica-applicata.html)
