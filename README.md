# juritools

Package permettant la pseudonymisation des décisions de justice des bases JURINET et JURICA ainsi que celles annotées via le logiciel de pseudonymisation de la cour de cassation.

## Installation

Cet utilitaire fonctionne sous Python 3.6+. Pour l'installer il faut effectuer les commandes suivantes :

```bash
git clone https://gitlab.com/openjustice/nlp/juritools.git
cd juritools
pip install .
```

## Utilisation

### **Prediction**

Lorsque vous avez fini d'entraîner votre classifieur, sérialisé dans un fichier  *pt*, vous pouvez l'utiliser sur n'importe quelle décision de justice provenant de la BDD Jurinet ou Jurica afin d'en extraire les entités d'intérêt. Pour ce faire, vous aurez besoin de précisier d'une part le modèle sérialisé et d'autre part le *tokenizer* que vous souhaitez appliquer, de préférence celui utilisé pour dans la phase de *preprocessing*.

```python
from juritools.predict import load_ner_model, JuriTagger
from jurispacy_tokenizer import JuriSpacyTokenizer

# Load your model and the tokenizer used in juritools library
model = load_ner_model('your/classifier/model.pt')
tokenizer = JuriSpacyTokenizer()

# Instantiate your JuriTagger object with the model and the tokenizer
juritag = JuriTagger(tokenizer, model)
# Predict entities of interest on a court decision
juritag.predict(text)
```

Les prédictions obtenues sont accessibles *via* la méthode *juritag.get_entity_json_from_flair_sentences()*. Elles sont égalements disponibles dans l'attribut *juritag.flair_sentences*

### **Postprocessing**

Une fois les entitiés obtenues à l'aide du modèle d'apprentissage automatique, nous pouvons utiliser un certain nombre de méthodes pour débusquer les entités non détectées par le modèle ainsi que pour lever des doutes sur la qualtié des prédictions. Plusieurs classes héritent de la classe *PostProcess* pour effectuer ces traitement. Cette classe prend en entrée une liste des entités (de type **NamedEntity**), une liste de vérifications manuelles à effectuer (de type **str**) et les métadonnées associées à la décisions (de type **pandas DataFrame**), si celles-ci existent. Les classes héritées sont les suivantes :

- *PostProcessFromText* prend en entrée le texte de la décision de justice ;
- *PostProcessFromSents* prend en entrée les phrases flair (de type **flair Sentence**) provenant de la classe JuriTagger après prédiction ;
- *PostProcessFromEntities*.

```python
from juritools.postprocessing import PostProcessFromText, PostProcessFromEntities, PostProcessFromSents
"""
Instantiate your PostProcess object with the text of the court decision,
the output of juritag.get_entity_json(), if the text is in a xml format,
and the metadata store in a pandas DataFrame if they exist
"""
predictions = get_entity_json_from_flair_sentences()
postpro_text = PostProcessFromText(text, predictions, manual_checklist=[], metadata=None)
postpro_sents = PostProcessFromSents(juritag.flair_sentences, postpro_text.entities, manual_checklist=[], metadata=None)
postpro_entities = PostProcessFromEntities(postpro_ents.entities, manual_checklist=[], metadata=None)
```

Methods available are as follows :

- [postpro_text.match_from_category()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_text.py#L24)
- [postpro_text.check_metadata()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_text.py#L180)
- [postpro_text.match_regex()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_text.py#L83)
- [postpro_text.juvenile_facility_entities()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_text.py#L247)
- [postpro_text.check_cadastre()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_text.py#L213)
- [postpro_text.check_compte_bancaire()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_text.py#L231)
- [postpro_text.manage_quote()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_text.py#L309)
- [postpro_text.manage_le()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_text.py#L277)
- [postpro_entities.match_physicomorale()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_entities.py#L18)
- [postpro_entities.change_pro_to_physique()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_entities.py#L52)
- [postpro_entities.manage_natural_persons()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_entities.py#L115)
- [postpro_entities.manage_year_in_date()](https://github.com/Cour-de-cassation/nlp-juritools/blob/ecfe17e4ebfb5082c9d226f523a81ad27d426bd2/juritools/postprocessing/postprocess_from_entities.py#L158)
- [postpro_entities.check_len_entities()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_entities.py#L233)
- [postpro_entities.check_entities()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_entities.py#L159)
- [postpro_entities.check_similarities()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_entities.py#L197)
- [postpro_sents.match_against_case()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_sents.py#L28)
- [postpro_sents.match_cities()](https://github.com/Cour-de-cassation/nlp-juritools/blob/197ffc0abf550f340b2ec695621208591cad3dbc/juritools/postprocessing/postprocess_from_sents.py#L52)
- [postpro_sents.match_facilities()](https://github.com/Cour-de-cassation/nlp-juritools/blob/0fa3f9d52af508e47d6a4d60b323377f78a31afe/juritools/postprocessing/postprocess_from_sents.py#L122)