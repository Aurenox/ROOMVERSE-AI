from copy import deepcopy
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta

from .content import fresh_virtual_case, scanner_case
from .round_ai import GeneratedRound, evidence_bank, generate_round
from .models import Game


def response_for(case):
    bank=evidence_bank(case)
    ids=(["image-0","image-1","mission-2","connection-0","sequence-0"]
         if case["id"] != "scanner" else ["mission-0","mission-1","mission-2","connection-0","sequence-0"])
    if "connection-0" not in bank:
        ids=list(bank)
    return GeneratedRound(title="The Unfinished Evidence Review",intro="A fresh inspection of this scene reveals a disputed record. Reconstruct the visitors' route using the supplied fictional evidence.",objective="Resolve the disputed route using the reliable records.",questions=[dict(
        evidence_id=key,question=f"Detective, {bank[key]['target']}",options=bank[key]['options'],answer=bank[key]['answer'],
        hints=["Recall the confirmed case records.","Link the visitor to the object.","Compare the possible destinations."],
        explanation="The independently confirmed records establish this answer.") for key in ids])


@override_settings(GEMINI_API_KEY="")
class RoundGenerationTests(TestCase):
    @patch("cases.round_ai.generate")
    def test_generated_round_and_immutable_local_fallback(self, provider):
        for case in [fresh_virtual_case("midnight"),scanner_case(["lamp","book"],"Detective","Professional")]:
            original=deepcopy(case)
            provider.return_value=response_for(case)
            result=generate_round(case,[])
            self.assertEqual(result['source'],'Gemini generated')
            self.assertEqual(len(result['puzzles']),5)
            self.assertEqual(result['puzzles'][0]['answer'],case['puzzles'][0]['answer'])
            self.assertEqual(result['puzzles'][1].get('changed_image'),case['puzzles'][1].get('changed_image'))
            self.assertEqual(case,original)
            provider.return_value=None
            fallback=generate_round(case,[])
            self.assertEqual(fallback['source'],'Puzzle engine fallback')
            self.assertEqual(fallback['puzzles'],original['puzzles'])

    @patch("cases.round_ai.generate")
    def test_wrong_answers_duplicates_repeats_and_private_data_rejected(self, provider):
        case=fresh_virtual_case('vault')
        valid=response_for(case)
        mutations=[]
        wrong=valid.model_copy(deep=True);wrong.questions[0].answer="Invented answer";mutations.append(wrong)
        duplicate=valid.model_copy(deep=True);duplicate.questions[1]=duplicate.questions[0];mutations.append(duplicate)
        private=valid.model_copy(deep=True);private.intro="Email someone@example.com to solve this case.";mutations.append(private)
        unknown=valid.model_copy(deep=True);unknown.questions[2].evidence_id="invented";mutations.append(unknown)
        for response in mutations:
            provider.return_value=response
            self.assertEqual(generate_round(case,[])['generation'],'engine')
        provider.return_value=valid
        old=generate_round(case,[])
        self.assertEqual(generate_round(case,[old,old])['generation'],'engine')

    @patch("cases.api.generate_round")
    def test_api_saves_generated_questions_and_keeps_answers_private(self, generate):
        def author(case, history):
            with patch('cases.round_ai.generate',return_value=response_for(case)):
                return generate_round(case,history)
        generate.side_effect=author
        response=self.client.post('/api/start/',{'scene':'midnight'},content_type='application/json')
        self.assertEqual(response.status_code,201)
        data=response.json()
        self.assertEqual(data['source'],'Gemini generated')
        self.assertNotIn('puzzles',data)
        game=Game.objects.get(pk=data['game_id'])
        self.assertEqual(game.case['generation'],'gemini')
        Game.objects.filter(pk=game.pk).update(deadline=timezone.now()-timedelta(seconds=1))
        current=self.client.get(f'/api/games/{game.pk}/').json()
        self.assertNotIn('answer',current['question'])
        self.assertNotIn('explanation',current['question'])
        self.assertEqual(current['question']['question'],game.case['puzzles'][0]['question'])


class SemanticRepetitionTests(TestCase):
    def test_rephrasing_cannot_reset_a_targets_exposure_count(self):
        from .round_ai import eligible
        from .stories import exposures, question_key
        case=fresh_virtual_case('observatory')
        target=case['puzzles'][0]['question']
        history=[]
        for wording in ['Rephrased question number one?', 'Another wording for the same pictured fact?']:
            old=deepcopy(case)
            old['puzzles'][0].update(question=wording,source_question=target)
            history.append(old)
        self.assertEqual(exposures(history)[question_key(target)],2)
        candidate=deepcopy(case)
        candidate['puzzles'][0].update(question='Yet another rewrite of this same target?',source_question=target)
        self.assertFalse(eligible(candidate,history))

    def test_legacy_gemini_image_rewrites_are_recognized(self):
        from .content import VISUAL_CLUES
        from .stories import exposures,question_key
        prompt,options,answer=VISUAL_CLUES['observatory'][0]
        old={'id':'observatory','puzzles':[dict(question='Name the largest instrument you saw.',options=options,answer=answer,generation_target='image-0')]}
        self.assertEqual(exposures([old])[question_key(prompt)],1)
        new=fresh_virtual_case('observatory',old,[old])
        self.assertNotIn(prompt,[q['question'] for q in new['puzzles']])

    @patch('cases.round_ai.generate')
    def test_gemini_round_preserves_source_targets(self,provider):
        case=fresh_virtual_case('observatory')
        provider.return_value=response_for(case)
        result=generate_round(case,[])
        self.assertEqual(result['generation'],'gemini')
        self.assertTrue(all(q.get('source_question') for q in result['puzzles']))
