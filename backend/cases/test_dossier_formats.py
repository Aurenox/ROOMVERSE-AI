from unittest.mock import patch
from django.test import TestCase
from .content import fresh_virtual_case, scanner_case
from .round_ai import evidence_bank


class DossierFormatTests(TestCase):
    def test_new_formats_do_not_reintroduce_the_witness_template(self):
        for family in ['inventory_audit','event_reconstruction','access_routes']:
            for difficulty in ['Beginner','Intermediate','Professional']:
                with patch('cases.dossier_formats.choose_format',return_value=family):
                    case=scanner_case(['lamp','book','key','globe'],'Detective',difficulty)
                headings=[label for label,value in case['exhibits']]
                for forbidden in ['Camera arrival order','Opening inventory','Closing inventory','Rooms in this case','Fictional case rules']:
                    self.assertNotIn(forbidden,headings)
                self.assertFalse(any(label.startswith(('Witness statement:','Confirmed record:')) for label in headings))
                self.assertEqual(len(case['puzzles']),5)
                self.assertEqual(len(evidence_bank(case)),5)
                self.assertFalse(any('carrier' in item['target'].lower() for item in evidence_bank(case).values()))
                for q in case['puzzles']:
                    self.assertEqual(len(set(q['options'])),4)
                    self.assertIn(q['answer'],q['options'])
                proof=case['evidence_model']
                if family=='inventory_audit':
                    computed=[a+b-c+d-e for a,b,c,d,e in zip(proof['opening'],proof['received'],proof['sent'],proof['returned'],proof['held'])]
                    self.assertEqual(computed,proof['expected'])
                    self.assertEqual([i for i in range(4) if computed[i]!=proof['observed'][i]],[proof['culprit']])
                    self.assertEqual(sum(computed)-sum(proof['observed']),proof['shortage'])
                elif family=='event_reconstruction':
                    self.assertEqual(proof['times'][-1],proof['base']+sum(proof['gaps']))
                    self.assertTrue(all(a<b for a,b in zip(proof['times'],proof['times'][1:])))
                else:
                    permitted=[name for name,path in proof['routes'].items() if proof['closed'] not in path]
                    self.assertEqual(permitted,[proof['authorized']])
                    self.assertNotIn(proof['missing'],proof['held'])

    def test_formats_rotate_and_visual_rounds_are_retained(self):
        history=[]
        for _ in range(12):
            case=fresh_virtual_case('observatory',history=history)
            if history:self.assertNotEqual(case['dossier_format'],history[-1]['dossier_format'])
            self.assertEqual(len(case['puzzles']),5)
            self.assertEqual(list(evidence_bank(case))[:2],['image-0','image-1'])
            history.append(case)
        self.assertEqual({case['dossier_format'] for case in history[:4]}, {'inventory_audit','event_reconstruction','access_routes','witness_logic'})
