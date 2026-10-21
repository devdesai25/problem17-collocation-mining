# Corpus provenance

This directory holds the analysis corpus: real municipal meeting transcripts, one agenda-item segment per file. The files are the text the pipeline reads. No audio was downloaded.

## Source

- Name: MeetingBank (Hu et al., ACL 2023)
- Hugging Face dataset: https://huggingface.co/datasets/huuuyeah/meetingbank
- File retrieved: `test.json` (JSONL), https://huggingface.co/datasets/huuuyeah/meetingbank/resolve/main/test.json
- Paper: https://arxiv.org/abs/2305.17529
- Zenodo record cited by the dataset card: https://zenodo.org/record/7989108
- Retrieval date: 2026-10-05
- License on the Hugging Face dataset card (`license` field in the README front matter): CC BY-NC-SA 4.0 (Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International). https://creativecommons.org/licenses/by-nc-sa/4.0/
- The assignment brief described MeetingBank as CC BY 4.0. The dataset card for the snapshot actually downloaded says `cc-by-nc-sa-4.0`. This note follows the card, not the brief.

## Why this source

The AMI Meeting Corpus was inspected first (`edinburghcstr/ami`, config `ihm`). Its parquet shards embed audio (about 200–300 MB each). Loading them through `datasets` tries to decode the audio column and failed here without `torchcodec`. Within the retrieval budget the text-only MeetingBank JSONL was used instead. VoxPopuli English parquet shards are larger still (about 0.9–3 GB) because they also carry audio, so they were not downloaded. Only the `transcript` field of MeetingBank was kept.

## What was kept

MeetingBank `test.json` contains 862 agenda-item segments and about 2.3 million whitespace tokens. The analysis corpus is a deterministic subset, not the full benchmark and not the `train.json` split.

Selection rule (no random seed; the order is a pure sort):

1. Keep segments whose whitespace token count is between 1400 and 3200 inclusive.
2. Group by city prefix of `uid` (the substring before the first underscore).
3. Sort cities by name, and segments within a city by `uid`.
4. Round-robin across cities until the cumulative whitespace token count reaches at least 65000.

Result: 28 files, 66924 whitespace tokens, 377488 bytes.

Each row in the JSONL is one agenda item (`uid`), not a full multi-hour council meeting. The dataset card describes full meetings as much longer (on the order of 28 thousand tokens). These files are the segment transcripts MeetingBank published for summarization.

Cities represented: Alameda, Boston, Denver, King County, Long Beach, Seattle.

## Token count

- Raw whitespace tokens, as stored in these files: **66924**.
- Processed tokens after sentence segmentation, cleaning, and lemmatization are written by `src/pipeline.py` into `reports/corpus_stats.json` (the count the association measures actually use). A copy of that processed count is repeated under the stats block below when the pipeline has been run.

## Limitations

- Sample of one split, not the 1,366 meetings in the full MeetingBank collection.
- Segment-level agenda items, so some cross-segment repetition of formulaic language is missing and some topics are over-represented (a single proclamation or land-use hearing).
- Transcripts contain ASR and clerk-style disfluency: false starts, missing punctuation, spelled numbers, and name errors.
- License is non-commercial (NC) plus share-alike. Do not treat this checkout as CC BY.
- No audio, video, minutes PDFs, or summaries are included. Summaries were not used as text.

## Per-file inventory

| file | uid | city | bytes | sha256 | whitespace tokens |
| --- | --- | --- | ---: | --- | ---: |
| `01_alamedacc_01072020_2020_7531.txt` | AlamedaCC_01072020_2020-7531 | AlamedaCC | 15754 | `69fd6a7625a8b648f3d52508096d3eae221bfb3c2124d9b130c3967f578181d1` | 2641 |
| `02_bostoncc_03022022_2022_0323.txt` | BostonCC_03022022_2022-0323 | BostonCC | 16643 | `52807608d863d836dae1bff4beff79a994c357f6434890ea532f90c941545b6d` | 2884 |
| `03_denvercitycouncil_01092017_16_1125.txt` | DenverCityCouncil_01092017_16-1125 | DenverCityCouncil | 18134 | `e0ff0f8ff94ff08534ebd143ed0725770723c80472ffd24701e69f7b8e7e750a` | 3081 |
| `04_kingcountycc_02032021_2021_0008.txt` | KingCountyCC_02032021_2021-0008 | KingCountyCC | 17202 | `8bc82d78af932c8572b960354df8b87ded74e495a3b40a729034bfdd9b3e5d12` | 2998 |
| `05_longbeachcc_01172017_17_0030.txt` | LongBeachCC_01172017_17-0030 | LongBeachCC | 14656 | `9ee97580be358d47c8d2eee344d8263e9b59b94be91afc32eef052bd6f2409e8` | 2701 |
| `06_seattlecitycouncil_02042019_res_31861.txt` | SeattleCityCouncil_02042019_Res 31861 | SeattleCityCouncil | 15550 | `857956bd894878b9affb1a0ae8211d55470352b0a028049e53953618b602e8d8` | 2696 |
| `07_alamedacc_02052019_2019_6387.txt` | AlamedaCC_02052019_2019-6387 | AlamedaCC | 10085 | `94ceb6a51f0455cfb03729068519dd6989020850d3bfd2203052a59c55b62d04` | 1822 |
| `08_bostoncc_03302022_2022_0438.txt` | BostonCC_03302022_2022-0438 | BostonCC | 7995 | `9419c52fd40cae64baef5819bcb4cea59c8c387d7c5a9aea6b7a9383c65417f4` | 1405 |
| `09_denvercitycouncil_01102022_22_0041.txt` | DenverCityCouncil_01102022_22-0041 | DenverCityCouncil | 12233 | `8c8c9d1d15c3bed7b2c2d42b6c499b60b27c33c4434a68d7618e8a7a0da33911` | 2161 |
| `10_kingcountycc_02032021_2021_0013.txt` | KingCountyCC_02032021_2021-0013 | KingCountyCC | 18257 | `6ee5f93cdf44483133fba80c42ace80a813e7eb1646e52e115a88eef70717f0e` | 3198 |
| `11_longbeachcc_02072017_17_0063.txt` | LongBeachCC_02072017_17-0063 | LongBeachCC | 15724 | `f6d37184b2ed685fd13049f9ce9920b8174b211031cf159240e6d229129a2318` | 2877 |
| `12_seattlecitycouncil_02182020_res_31934.txt` | SeattleCityCouncil_02182020_Res 31934 | SeattleCityCouncil | 9259 | `c2a1e259a5b48476784117548569bf7322c076edec05496491aacb368ce17a0d` | 1631 |
| `13_alamedacc_04172018_2018_5378.txt` | AlamedaCC_04172018_2018-5378 | AlamedaCC | 10687 | `3ad9a5c919b843c4dd58f2739c9999c8cbe2506e08f866d31bec9b47fda79e6b` | 1931 |
| `14_bostoncc_04062022_2022_0467.txt` | BostonCC_04062022_2022-0467 | BostonCC | 13229 | `2ecf90f19a994f020a18b7dc8bf81c214930e89ac52bc92e24c3f7d441cd8e1b` | 2382 |
| `15_denvercitycouncil_01122015_14_1097.txt` | DenverCityCouncil_01122015_14-1097 | DenverCityCouncil | 8452 | `5d5fbcf21c31b76b682f6746a48d461b366a76af2b8e4832d8b0ef413e2c1dde` | 1482 |
| `16_kingcountycc_03292017_2017_0139.txt` | KingCountyCC_03292017_2017-0139 | KingCountyCC | 15314 | `6042ba187cc17a0b05f3a41293d4a6ccb7b14e1d8d01d48b531679714bc37d89` | 2674 |
| `17_longbeachcc_02092021_21_0103.txt` | LongBeachCC_02092021_21-0103 | LongBeachCC | 8612 | `6ac73a147190c344cdc8b027a3773b31ab542cfea989c7a6c04b163205f34457` | 1568 |
| `18_seattlecitycouncil_03162020_cb_119755.txt` | SeattleCityCouncil_03162020_CB 119755 | SeattleCityCouncil | 17596 | `9c1aa1b6a313dbc569fe4de20faac4c6248a69f18cd7ff4303a243bcaaf05414` | 3046 |
| `19_alamedacc_04212015_2015_1500.txt` | AlamedaCC_04212015_2015-1500 | AlamedaCC | 14743 | `6830083b789f96c6a1bfd8085ed38c124da68e06e47d76fed9f0e5713a69479b` | 2642 |
| `20_bostoncc_06082022_2022_0726.txt` | BostonCC_06082022_2022-0726 | BostonCC | 14598 | `8995aa8249b68557cb42d5030f4ec642fa18a7ac7f4b2bf41e5e938303ec5416` | 2667 |
| `21_denvercitycouncil_01292018_18_0009.txt` | DenverCityCouncil_01292018_18-0009 | DenverCityCouncil | 10373 | `638c2ab83e7e6937b78742258a81403c088408cbb6a6e142a855f12c01eed95e` | 1913 |
| `22_kingcountycc_04152019_2019_0103.txt` | KingCountyCC_04152019_2019-0103 | KingCountyCC | 8315 | `1214d902226f140a27ddd760b9c2e4ca40fa4016a748e6216530ad0264d7f3bc` | 1438 |
| `23_longbeachcc_02162016_16_0138.txt` | LongBeachCC_02162016_16-0138 | LongBeachCC | 13673 | `33039c6919e4dbf420eaf654f07dcd175c4bf55f0837e2751473de3d695dff1d` | 2479 |
| `24_seattlecitycouncil_03182019_res_31871.txt` | SeattleCityCouncil_03182019_Res 31871 | SeattleCityCouncil | 17144 | `9c3d6dcb8cc8b61622d79f8d94c1f7aeba86e6e0681bb2a6e3b4857dbe27f4dc` | 2913 |
| `25_alamedacc_05072019_2019_6796.txt` | AlamedaCC_05072019_2019-6796 | AlamedaCC | 10038 | `3181e09893dbb607a731018f540a6808afcbd45d97fcd471483da5b454e6ac48` | 1866 |
| `26_bostoncc_06292022_2022_0816.txt` | BostonCC_06292022_2022-0816 | BostonCC | 14722 | `46bd6747e97484373a1a60814b52caebe0c7b76b2ea1a3c230ac60e869a82e39` | 2643 |
| `27_denvercitycouncil_02012016_16_0071.txt` | DenverCityCouncil_02012016_16-0071 | DenverCityCouncil | 16264 | `2a33554e50439e6d6ba31e21fce7033c757412f61b6f2cb7b59e805d3e2e9fc5` | 3016 |
| `28_kingcountycc_05162018_2018_0149.txt` | KingCountyCC_05162018_2018-0149 | KingCountyCC | 12236 | `15c05a48a58774e2b2d70dd508d8ca548c0f9e8752c93a2180ce3f20c563ea2f` | 2169 |

| **total** | | | **377488** | | **66924** |

## Processed-token block

The pipeline refreshes the next two lines. Until it has run, processed counts live only in `reports/corpus_stats.json` after the first execution.

<!-- PROCESSED_STATS_START -->
processed_tokens: 67046
processed_sentences: 5318
processed_lemmas: 4437
<!-- PROCESSED_STATS_END -->

