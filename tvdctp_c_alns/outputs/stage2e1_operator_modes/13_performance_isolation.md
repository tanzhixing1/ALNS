# Performance isolation

Three 12-iteration paper runs show:

- mode resolution: 0.0030–0.0104 ms;
- registry construction: 0.1711–0.2837 ms, once per run;
- two roulette calls plus action lookup: 0.2695–0.2955 ms/iteration;
- destroy calls = repair calls = 12 in every run.

The Baseline-P seed 29 retains 653 objective and 909 checker calls exactly.
Candidate profiles and adapter behavior are unchanged. Registry construction is
outside all candidate/objective/checker loops. No candidate truncation,
performance optimization, or search-semantic change was made. Wall clock is
diagnostic only.
