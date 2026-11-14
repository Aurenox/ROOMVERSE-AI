from copy import deepcopy
import json
from django.test import TestCase
from .archive import preserve, duplicate, DuplicateRound, archive_history
from .content import fresh_virtual_case, scanner_case
from .models import Game, RoundArchive, ArchiveFingerprint


class ArchiveTests(TestCase):
    def test_preserves_full_round_independently_of_game_and_owner(self):
        case=fresh_virtual_case('observatory')
        game=Game.objects.create(guest='one',case=case)
        preserve(case)
        game.delete()
        saved=RoundArchive.objects.get().payload
        self.assertEqual(saved,json.loads(json.dumps(case)))
        self.assertEqual(saved['puzzles'][0]['answer'],case['puzzles'][0]['answer'])
        self.assertTrue(duplicate(case))
        self.assertEqual(archive_history('observatory'),[json.loads(json.dumps(case))])
        self.assertEqual(archive_history('midnight'),[])

    def test_reworded_target_and_reordered_options_cannot_bypass_index(self):
        case=fresh_virtual_case('vault')
        case['puzzles'][0]['source_question']=case['puzzles'][0]['question']
        preserve(case)
        changed=deepcopy(case)
        changed['intro']='A different opening for the same already archived evidence.'
        changed['story_title']='A changed title'
        for index,q in enumerate(changed['puzzles']):
            q['source_question']=q.get('source_question',q['question'])
            q['question']=f'Reworded detective question for clue {index}?'
            q['options'].reverse()
        self.assertTrue(duplicate(changed))
        count=ArchiveFingerprint.objects.count()
        with self.assertRaises(DuplicateRound):preserve(changed)
        self.assertEqual(RoundArchive.objects.count(),1)
        self.assertEqual(ArchiveFingerprint.objects.count(),count)

    def test_backfill_is_idempotent_and_scanner_content_is_not_shared(self):
        case=fresh_virtual_case('library')
        preserve(case,backfill=True);preserve(case,backfill=True)
        self.assertEqual(RoundArchive.objects.count(),1)
        private=scanner_case(['lamp','book'],'Detective','Beginner')
        preserve(private)
        self.assertFalse(duplicate(private))
        self.assertEqual(RoundArchive.objects.count(),1)

    def test_changed_story_with_exact_question_still_duplicates(self):
        case=fresh_virtual_case('hotel');preserve(case)
        next_case=fresh_virtual_case('hotel',history=[case])
        next_case['puzzles'][2]=deepcopy(case['puzzles'][2])
        next_case['puzzles'][2]['question']=next_case['puzzles'][2]['question'].upper()+' !!!'
        self.assertTrue(duplicate(next_case))
