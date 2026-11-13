### X2 Claude，20 主分析 E

單位：logical tokens。各列是已歸因值；末列差額仍計入總額。

| Stage | parent cache reads | parent rest | subagents cache reads | subagents rest |
|---|---:|---:|---:|---:|
| prep | 2,511,469 | 734,301 | 0 | 0 |
| S5 | 992,382 | 133,996 | 409,821 | 349,249 |
| S6 | 439,938 | 55,061 | 235,921 | 305,362 |
| S7 | 5,567,035 | 408,963 | 659,659 | 939,533 |
| S8 | 355,344 | 33,936 | 798,739 | 598,259 |
| S9 | 6,731,704 | 381,425 | 874,667 | 944,897 |
| final | 7,169,298 | 258,083 | 0 | 0 |
| parent_output_unallocated | 0 | 557,308 | 0 | 0 |
| unknown | 577,631 | 25,759 | 0 | 16,784 |
| 未歸因（actor 不明） | — | 347,254 | — | — |

總計：cache reads **27,323,608**；rest **6,090,170**；logical **33,413,778**。

### X2 Codex，20 主分析 E

單位：logical tokens。各列是已歸因值；末列差額仍計入總額。

| Stage | parent cache reads | parent rest | subagents cache reads | subagents rest |
|---|---:|---:|---:|---:|
| prep | 1,365,888 | 411,855 | 0 | 0 |
| S5 | 6,180,096 | 389,912 | 1,627,136 | 345,923 |
| S6 | 4,729,472 | 95,626 | 1,332,096 | 184,521 |
| S7 | 8,484,224 | 158,628 | 4,742,784 | 604,903 |
| S8 | 4,679,936 | 121,703 | 1,658,624 | 318,964 |
| S9 | 10,426,752 | 169,440 | 5,023,488 | 617,029 |
| final | 5,183,744 | 141,576 | 0 | 0 |
| 未歸因（actor 不明） | — | 0 | — | — |

總計：cache reads **55,434,240**；rest **3,560,080**；logical **58,994,320**。

### plan-review Claude E，1 次

單位：logical tokens。各列是已歸因值；末列差額仍計入總額。

| Stage | parent cache reads | parent rest | subagents cache reads | subagents rest |
|---|---:|---:|---:|---:|
| prep | 140,630 | 47,629 | 0 | 0 |
| S5 | 102,770 | 11,096 | 787,716 | 95,405 |
| S6 | 187,363 | 7,040 | 109,494 | 63,331 |
| S7 | 1,587,134 | 66,608 | 1,145,956 | 221,001 |
| S8 | 272,640 | 11,067 | 794,907 | 112,019 |
| S9 | 1,268,616 | 36,778 | 9,966,103 | 467,245 |
| final | 770,709 | 25,589 | 0 | 0 |
| parent_output_unallocated | 0 | 67,563 | 0 | 0 |
| 未歸因（actor 不明） | — | 113,794 | — | — |

總計：cache reads **17,134,038**；rest **1,346,165**；logical **18,480,203**。

### 每次完成作答的總額

原始 locator：`x2/runs/{cell}-{part}/raw/E-{case}.a{attempt}.jsonl`；`anatomy.json` 保存完整短 locator、逐 agent／stage 與 source hash。

| Case | Claude cache | Claude rest | Codex cache | Codex rest |
|---|---:|---:|---:|---:|
| auditlog | 1,064,205 | 310,875 | 2,307,456 | 135,832 |
| carts | 1,386,851 | 299,127 | 2,745,856 | 169,690 |
| clean | 1,161,656 | 230,647 | 2,243,328 | 148,613 |
| cron | 1,285,097 | 277,204 | 2,726,400 | 178,299 |
| dashboard | 1,296,627 | 334,807 | 3,028,736 | 184,813 |
| digest | 1,264,266 | 282,170 | 2,645,760 | 182,643 |
| events | 1,051,139 | 210,687 | 2,243,968 | 131,083 |
| export | 1,451,932 | 302,062 | 2,769,152 | 184,926 |
| flags | 1,282,572 | 262,290 | 3,479,936 | 207,793 |
| invites | 1,475,890 | 299,584 | 3,097,728 | 167,642 |
| invoices | 1,609,716 | 316,088 | 2,569,856 | 177,331 |
| metering | 1,334,553 | 325,657 | 3,514,496 | 178,866 |
| migrations | 1,327,372 | 335,050 | 2,872,192 | 161,068 |
| payouts | 1,291,890 | 308,270 | 2,880,384 | 188,112 |
| ratelimit | 1,347,336 | 273,856 | 2,855,424 | 165,643 |
| registry | 1,494,257 | 314,407 | 2,064,000 | 220,803 |
| resets | 1,367,769 | 281,587 | 2,387,712 | 201,087 |
| search | 1,671,307 | 292,783 | 2,581,376 | 159,382 |
| sessions | 1,454,131 | 342,050 | 2,623,744 | 163,480 |
| supplier | 1,356,996 | 313,513 | 2,919,808 | 154,592 |
| uploads | 1,377,168 | 323,140 | 2,970,368 | 164,548 |
| webhooks | 1,183,673 | 295,650 | 2,393,856 | 213,530 |

### Pilot 與未計入品質的中斷

| Cell / case / status | logical | cache | rest | 未歸因 rest |
|---|---:|---:|---:|---:|
| claude / dashboard / usage_limit | 337,643 | 230,413 | 107,230 | 2,471 |
| claude / carts / usage_limit | 1,364,955 | 1,096,205 | 268,750 | 15,775 |
| claude / orders / pilot | 1,492,115 | 1,271,392 | 220,723 | 8,052 |
| codex / orders / pilot | 2,531,919 | 2,400,128 | 131,791 | 0 |

### 各 planted defect 的最早可見 reviewer 回報

每個 ID 在兩格都是 **S5** 的初次回報；不是對中間報告另做評分。逐 ID 的原文摘錄、raw line、final 既有兩家 grade 見 `finding-provenance.json`。

| Case | IDs（Claude / Codex 都在 S5） | Claude S5 raw line | Codex S5 rollout raw line |
|---|---|---:|---:|
| auditlog | C1, C2, M1 | 78 | 32 |
| carts | C1, M1, M2 | 81 | 42 |
| cron | C1, M1, M2 | 88 | 47 |
| digest | C1, M1, M2 | 89 | 33 |
| export | C1, C2, M1 | 79 | 39 |
| flags | C1, M1, M2 | 83 | 34 |
| invites | C1, C2, M1 | 112 | 39 |
| invoices | C1, C2, M1 | 103 | 41 |
| metering | C1, C2, M1 | 101 | 55 |
| migrations | C1, C2, M1 | 108 | 43 |
| payouts | C1, C2, M1 | 111 | 40 |
| ratelimit | C1, M1, M2 | 75 | 37 |
| resets | C1, M1, M2 | 84 | 41 |
| search | C1, C2, M1 | 106 | 46 |
| uploads | C1, C2, M1 | 86 | 39 |
| webhooks | C1, M1, M2 | 67 | 32 |
