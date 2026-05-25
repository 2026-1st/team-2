from __future__ import annotations

import unittest

import pandas as pd

from team2_surrender.modeling import assert_no_group_leakage, make_group_split


class ModelingSplitTests(unittest.TestCase):
    def test_group_split_has_no_match_leakage(self):
        rows = []
        for group in range(20):
            for team_id in (100, 200):
                rows.append({"match_id": f"KR_{group}", "team_id": team_id, "team_surrendered": team_id == 200})
        df = pd.DataFrame(rows)
        split = make_group_split(df, group_col="match_id", random_state=7)
        assert_no_group_leakage(df, split, group_col="match_id")
        self.assertGreater(len(split.train_idx), 0)
        self.assertGreater(len(split.valid_idx), 0)
        self.assertGreater(len(split.test_idx), 0)


if __name__ == "__main__":
    unittest.main()
