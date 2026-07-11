# Regret semantic cases

Controlled concrete-move ranking tests:

| Case | Candidate costs | Best mode | Second mode | Expected regret | Actual |
| --- | --- | --- | --- | ---: | ---: |
| van + van | van 10, van 12, drone 20 | van | van | 2 | 2 |
| drone + drone | drone 8, drone 9, van 15 | drone | drone | 1 | 1 |
| van + drone | van 7, drone 11, van 13 | van | drone | 4 | 4 |
| drone + van | drone 6, van 10, drone 12 | drone | van | 4 | 4 |

The second strategy is selected from the unified Ω(i), not from the other service mode.
