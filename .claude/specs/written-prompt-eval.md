# Written Prompt Generation — Eval Report

- Model: `gemini-2.0-flash`
- Tuples: 10
- Grammar targets: 28
- Targets marked forced=true: 27
- **Hit rate: 96.4%** (threshold: 80%)
- **Gate status: PASS**

## Per-tuple results

### 1. Ch. 12 — Le subjonctif présent (opinion_essay, ~150 words)

**Grammar targets**:
- subjonctif présent après expressions de doute et d'émotion
- conjonctions de subordination (bien que, avant que, à condition que)

**Vocab targets**: néanmoins, par ailleurs, souligner, envisager, certes

**Generated scenario**:

> L'intelligence artificielle (IA) est de plus en plus présente dans notre quotidien. Certains craignent qu'elle ne remplace un jour la créativité humaine, tandis que d'autres y voient un outil formidable pour l'augmenter. Rédigez un court essai dans lequel vous exprimez votre opinion sur ce sujet. Considérez les arguments pour et contre, et expliquez pourquoi vous pensez qu'il est essentiel que nous restions vigilants quant à son développement, même si nous reconnaissons son potentiel.

**Theme**: IA et créativité  
**Why this forces grammar** (generator's own reasoning): The prompt demands the subjonctif présent after expressions of doubt (craignent que) and necessity (il est essentiel que). The contrasting opinions ('bien que nous reconnaissions') necessitates 'bien que' + subjonctif. The need to express vigilance introduces 'à condition que' constructions.

**Critic verdict**:

| Grammar target | Forced? | Rationale |
|---|---|---|
| subjonctif présent après expressions de doute et d'émotion | yes | The scenario explicitly presents opposing viewpoints and asks for an opinion, naturally leading to expressions of doubt, uncertainty, or emotional reactions to the potential impacts of AI, thus making the subjunctive a natural choice. |
| conjonctions de subordination (bien que, avant que, à condition que) | yes | The prompt asks for consideration of arguments for and against AI and emphasizes the need for vigilance 'even if' its potential is recognized, creating a clear structural pressure for using concessive conjunctions like 'bien que' or conditional ones like 'à condition que'. |

**Tuple hit rate**: 2/2

---

### 2. Ch. 7 — Passé composé et imparfait (story_continuation, ~200 words)

**Grammar targets**:
- passé composé pour actions ponctuelles
- imparfait pour description et arrière-plan
- accord du participe passé avec avoir

**Vocab targets**: soudain, tandis que, jadis, le lendemain, à cette époque-là

**Generated scenario**:

> La vieille horloge de la gare émit son douzième coup. Jeanne frissonna, emmitouflée dans son manteau élimé. Elle attendait, assise sur un banc inconfortable, depuis des heures. Soudain, un haut-parleur grésilla, annonçant un retard indéterminé. Racontez la suite des événements, en intégrant les émotions et les souvenirs qui assaillent Jeanne durant cette attente.

**Theme**: Attente nocturne, gare  
**Why this forces grammar** (generator's own reasoning): The opening sets up an imperfect background description (weather, her state) against which punctual events in the passé composé will occur (the clock striking, the speaker announcement). The instruction to integrate emotions and memories further pushes imperfect for descriptions and passé composé for specific recalled events. The feminine name Jeanne forces the student to remember participe passé agreement rules.

**Critic verdict**:

| Grammar target | Forced? | Rationale |
|---|---|---|
| passé composé pour actions ponctuelles | yes | The prompt sets up a narrative where Jeanne is waiting and then something happens, naturally leading to the use of the passé composé to describe the sequence of events following the announcement. |
| imparfait pour description et arrière-plan | yes | The initial description of Jeanne, her feelings, and the setting (old clock, worn coat, uncomfortable bench) strongly encourages the use of the imparfait to provide background information and describe the ongoing state of affairs. |
| accord du participe passé avec avoir | no | While possible, it's not structurally forced. The student could easily write a continuation without needing to use verbs where the past participle agreement with 'avoir' is essential or frequent. |

**Tuple hit rate**: 2/3

---

### 3. Ch. 15 — Le conditionnel (letter_writing, ~150 words)

**Grammar targets**:
- conditionnel présent pour hypothèse
- conditionnel passé pour regret ou reproche
- si + imparfait / conditionnel

**Vocab targets**: j'aurais préféré, dans l'idéal, faute de, à ta place, il vaudrait mieux

**Generated scenario**:

> Imagine que tu es un(e) ami(e) proche de Sophie. Sophie a récemment raté un entretien d'embauche très important. Écris-lui une lettre de réconfort et de conseil. Exprime ton empathie, mais suggère également ce qu'elle aurait pu faire différemment. Si j'étais à sa place, j'essaierais de...

**Theme**: Amitié, conseils, regrets  
**Why this forces grammar** (generator's own reasoning): The prompt forces 'conditionnel passé' to express regret ('ce qu'elle aurait pu faire différemment'), 'conditionnel présent' for hypothetical advice, and 'si + imparfait / conditionnel' by asking what the writer would do in Sophie's place.

**Critic verdict**:

| Grammar target | Forced? | Rationale |
|---|---|---|
| conditionnel présent pour hypothèse | yes | Suggesting what Sophie could have done differently naturally leads to hypothetical situations expressed using the conditionnel présent. |
| conditionnel passé pour regret ou reproche | yes | Expressing regret or gently suggesting what Sophie *should have* done differently is a core element of the prompt, making the conditionnel passé a natural choice. |
| si + imparfait / conditionnel | yes | The prompt explicitly asks for advice using 'Si j'étais à sa place, j'essaierais de...', creating direct structural pressure for this construction. |

**Tuple hit rate**: 3/3

---

### 4. Ch. 9 — Pronoms relatifs (opinion_essay, ~150 words)

**Grammar targets**:
- pronoms relatifs composés (auquel, duquel, lequel)
- dont avec complément de nom
- ce qui, ce que, ce dont

**Vocab targets**: un phénomène, une cause, un enjeu, un impact, une conséquence

**Generated scenario**:

> La mondialisation est un phénomène complexe auquel on attribue de nombreux avantages, mais dont les conséquences sont parfois désastreuses. Parmi les enjeux auxquels les pays en développement sont confrontés, lequel vous semble le plus préoccupant ? Expliquez ce qui motive votre choix, en soulignant ce dont les pays riches devraient prendre conscience et ce que l'on pourrait faire pour atténuer les effets négatifs.

**Theme**: Mondialisation et développement  
**Why this forces grammar** (generator's own reasoning): The initial sentence directly seeds 'auquel' and 'dont'. The question then prompts the student to discuss an issue 'auxquels' developing countries are confronted with, 'ce qui' motivates their choice, 'ce dont' rich countries should be aware of, and 'ce que' could be done.

**Critic verdict**:

| Grammar target | Forced? | Rationale |
|---|---|---|
| pronoms relatifs composés (auquel, duquel, lequel) | yes | The prompt discusses complex issues and asks for explanations, naturally leading to the need to specify relationships between concepts, making compound relative pronouns a natural choice. |
| dont avec complément de nom | yes | The prompt asks about concerns and their effects, creating a natural need to express possession or belonging, making 'dont' a likely and idiomatic choice. |
| ce qui, ce que, ce dont | yes | The prompt explicitly asks for explanations of 'ce qui motive votre choix' and 'ce que l'on pourrait faire', creating direct structural pressure toward using these constructions. |

**Tuple hit rate**: 3/3

---

### 5. Ch. 3 — Les articles (journal_entry, ~100 words)

**Grammar targets**:
- articles partitifs (du, de la, des)
- absence d'article après expressions de quantité
- de à la place de du / de la en phrase négative

**Vocab targets**: beaucoup de, un peu de, manquer de, se passer de, avoir besoin de

**Generated scenario**:

> Cher journal, aujourd'hui, j'ai tenté de préparer un gâteau. J'avais beaucoup d'espoir, mais je me suis vite rendu compte que je manquais d'ingrédients essentiels. Je n'avais pas de farine, ni de beurre. Malgré tout, j'ai décidé de continuer, en improvisant avec un peu de sucre et des fruits. Finalement, ce n'était pas un chef-d'œuvre, mais j'ai appris qu'on peut se passer de certaines choses et quand même créer quelque chose.

**Theme**: Cuisine et improvisation  
**Why this forces grammar** (generator's own reasoning): The scenario forces articles partitifs by describing the ingredients the writer has or lacks (farine, beurre, sucre, fruits). It forces absence of articles with quantity expressions (beaucoup d'espoir, un peu de sucre). It forces 'de' instead of 'du/de la' in negative sentences (je n'avais pas de farine, ni de beurre).

**Critic verdict**:

| Grammar target | Forced? | Rationale |
|---|---|---|
| articles partitifs (du, de la, des) | yes | The scenario explicitly mentions missing ingredients, creating a natural context for using partitive articles to describe the quantities of ingredients that were available (or not). |
| absence d'article après expressions de quantité | yes | The scenario involves discussing quantities of ingredients, making the absence of articles after expressions of quantity a very natural and likely occurrence. |
| de à la place de du / de la en phrase négative | yes | The scenario explicitly states a lack of ingredients ('Je n'avais pas de farine, ni de beurre'), directly prompting the use of 'de' instead of 'du/de la' in negative sentences. |

**Tuple hit rate**: 3/3

---

### 6. Ch. 18 — Le gérondif et le participe présent (situational, ~150 words)

**Grammar targets**:
- gérondif pour exprimer la simultanéité ou la manière
- participe présent pour cause ou caractérisation

**Vocab targets**: tout en, en effet, de ce fait, par conséquent, compte tenu de

**Generated scenario**:

> Vous êtes responsable de la sécurité dans une usine chimique. Un nouvel employé vous demande des conseils pour éviter les accidents. Expliquez-lui, étape par étape, les mesures de sécurité à suivre lors de la manipulation de produits chimiques dangereux. Insistez sur l'importance de porter l'équipement de protection adéquat et de respecter scrupuleusement les consignes, tout en restant calme et concentré. Décrivez les conséquences possibles du non-respect de ces règles.

**Theme**: Sécurité au travail  
**Why this forces grammar** (generator's own reasoning): The prompt forces the use of the gérondif by requiring step-by-step instructions, which are best expressed by describing how something is done *while* doing something else. The use of 'restant calme et concentré' directly pulls the present participle to express the state of mind. Describing the consequences of not following the rules will likely use the present participle to explain the cause of the consequences.

**Critic verdict**:

| Grammar target | Forced? | Rationale |
|---|---|---|
| gérondif pour exprimer la simultanéité ou la manière | yes | The prompt asks for step-by-step instructions on how to handle chemicals safely, which naturally leads to using the gérondif to describe the manner in which actions should be performed (e.g., "en portant l'équipement"). |
| participe présent pour cause ou caractérisation | yes | The prompt requires explaining the consequences of not following the rules, which can be expressed using the present participle to indicate cause (e.g., "Ne respectant pas les consignes, vous risquez..."). |

**Tuple hit rate**: 2/2

---

### 7. Ch. 14 — La concordance des temps (story_continuation, ~200 words)

**Grammar targets**:
- concordance au passé (imparfait dans subordonnée)
- plus-que-parfait pour antériorité
- conditionnel pour futur dans le passé

**Vocab targets**: avoir annoncé que, savoir que, espérer que, la veille, le jour suivant

**Generated scenario**:

> La veille de son départ pour l'Antarctique, Jeanne a dîné avec ses parents. Elle leur a annoncé qu'elle avait tout préparé minutieusement, car elle ne voulait rien oublier. Sa mère, inquiète, lui a demandé de lui raconter en détail ce qu'elle ferait là-bas. Continuez le récit en décrivant la conversation entre Jeanne et sa mère. (environ 200 mots)

**Theme**: Voyage et famille  
**Why this forces grammar** (generator's own reasoning): The prompt forces *concordance des temps* by requiring a recounting of a past conversation. *Plus-que-parfait* is forced by the 'avait tout préparé' seed, which the student must then refer back to. *Conditionnel* is encouraged by the 'ce qu'elle ferait là-bas' seed, which the student must elaborate on.

**Critic verdict**:

| Grammar target | Forced? | Rationale |
|---|---|---|
| concordance au passé (imparfait dans subordonnée) | yes | The scenario sets up a past narrative where Jeanne is explaining her plans, naturally leading to subordinate clauses in the imparfait to describe ongoing or habitual actions in the past. |
| plus-que-parfait pour antériorité | yes | Jeanne is describing preparations she made *before* the conversation, creating a natural need for the plus-que-parfait to express actions completed before another point in the past. |
| conditionnel pour futur dans le passé | yes | Jeanne is describing what she *would* do in Antarctica, as related in the past, making the conditional tense the most natural way to express future actions from a past perspective. |

**Tuple hit rate**: 3/3

---

### 8. Ch. 6 — Accord du participe passé (journal_entry, ~150 words)

**Grammar targets**:
- accord du participe passé avec être
- accord du participe passé avec avoir + COD antéposé
- participe passé des verbes pronominaux

**Vocab targets**: les lettres que j'ai reçues, une fois rentré, s'être rendu compte, elles se sont parlé, ils se sont souvenus

**Generated scenario**:

> Imaginez que vous tenez un journal intime. Vous venez de rentrer d'un long voyage en Italie avec vos amies, Sophie et Léa. Décrivez une anecdote marquante qui s'est déroulée à Rome. Concentrez-vous sur les émotions que vous avez ressenties une fois rentrée à l'hôtel, et sur ce que vous ont dit vos amies à ce sujet. N'oubliez pas de mentionner les lettres que vous avez reçues après votre retour.

**Theme**: Voyage et souvenirs  
**Why this forces grammar** (generator's own reasoning): The prompt forces accord du participe passé with 'être' through the feminine plural 'vos amies' and the reflexive construction 's'est déroulée'. It forces accord with 'avoir' via the phrase 'les lettres que vous avez reçues'. It targets participe passé des verbes pronominaux through the directive to focus on emotions felt 'une fois rentrée' and what friends 'vous ont dit'.

**Critic verdict**:

| Grammar target | Forced? | Rationale |
|---|---|---|
| accord du participe passé avec être | yes | Describing a trip with friends and reflecting on it will naturally involve using verbs conjugated with 'être' to describe movement and states, thus requiring agreement of the past participle. |
| accord du participe passé avec avoir + COD antéposé | yes | Describing memories and anecdotes from the trip will likely involve mentioning things that were seen or experienced, creating opportunities for using 'avoir' with an anteposed COD, thus requiring agreement of the past participle. |
| participe passé des verbes pronominaux | yes | Reflecting on personal experiences and emotions in a diary entry will naturally lead to the use of pronominal verbs, requiring the correct agreement of the past participle. |

**Tuple hit rate**: 3/3

---

### 9. Ch. 20 — Le discours indirect (dialogue, ~150 words)

**Grammar targets**:
- transformation au discours indirect (changement de temps)
- transformation des marqueurs temporels (hier → la veille)
- verbes introducteurs (affirmer, prétendre, suggérer)

**Vocab targets**: il a déclaré que, elle a ajouté, selon lui, d'après elle, il aurait précisé

**Generated scenario**:

> Imaginez que vous êtes journaliste. Hier, vous avez interviewé deux figures politiques, Madame Dubois et Monsieur Lemaire, après un débat télévisé houleux sur la réforme des retraites. Rédigez un court article où vous rapportez leurs déclarations principales. Madame Dubois, visiblement agacée, avait quitté le plateau précipitamment. Monsieur Lemaire, lui, semblait plus mesuré, mais tout aussi ferme sur ses positions.

**Theme**: Politique, Réforme  
**Why this forces grammar** (generator's own reasoning): The prompt forces discours indirect by framing the task as reporting on a past interview. The past tense of the interview ('hier, vous avez interviewé') demands transformations of temporal markers ('hier' becomes 'la veille'). The instruction to report 'leurs déclarations principales' forces the use of reporting verbs like 'déclarer', 'ajouter', etc.

**Critic verdict**:

| Grammar target | Forced? | Rationale |
|---|---|---|
| transformation au discours indirect (changement de temps) | yes | The scenario explicitly asks for reporting the politicians' statements, making indirect speech the most natural and idiomatic approach. |
| transformation des marqueurs temporels (hier → la veille) | yes | Reporting on an event from 'hier' necessitates changing the time marker to 'la veille' when using indirect speech. |
| verbes introducteurs (affirmer, prétendre, suggérer) | yes | Reporting statements requires introductory verbs like 'affirmer,' 'prétendre,' or 'suggérer' to frame the reported speech. |

**Tuple hit rate**: 3/3

---

### 10. Ch. 11 — La voix passive (opinion_essay, ~150 words)

**Grammar targets**:
- voix passive avec être + participe accordé
- complément d'agent introduit par par ou de
- alternatives à la passive (on, se faire + infinitif)

**Vocab targets**: être mis en place, être reconnu, se voir attribuer, un dispositif, une mesure

**Generated scenario**:

> Un nouveau système de notation des enseignants a été mis en place dans votre région. Selon ce dispositif, une partie de l'évaluation se base sur les résultats des élèves aux examens, une autre sur les observations en classe, et une dernière sur les retours des parents. Certains estiment que cette mesure est un progrès, d'autres la considèrent comme une source de stress supplémentaire. Êtes-vous favorable à cette réforme ? Pourquoi ? Expliquez comment, selon vous, on pourrait améliorer l'évaluation des enseignants tout en tenant compte de leurs efforts et des spécificités de chaque établissement.

**Theme**: Éducation, évaluation  
**Why this forces grammar** (generator's own reasoning): The prompt forces passive voice by describing a system that *has been put in place.* It requires the student to discuss *how one could improve* (on) the system (alternative to passive). The phrase "selon ce dispositif" sets up the need to explain how teachers *are evaluated* by the system, and by whom (par or de).

**Critic verdict**:

| Grammar target | Forced? | Rationale |
|---|---|---|
| voix passive avec être + participe accordé | yes | The scenario discusses a system *being* implemented and evaluated, making the passive voice a natural and efficient way to describe the process and actions taken by the system or on the teachers. |
| complément d'agent introduit par par ou de | yes | Since the prompt involves a system of evaluation, specifying *by whom* the evaluation is conducted (e.g., 'par les parents', 'par les élèves') is a natural and idiomatic way to express agency in the passive constructions. |
| alternatives à la passive (on, se faire + infinitif) | yes | While the passive is natural, the prompt also allows for discussing how teachers *are being* evaluated, which can be rephrased using 'on' or 'se faire + infinitif' as alternatives to the passive voice to express the same idea with slightly different nuances. |

**Tuple hit rate**: 3/3

---
