# Cascade Digital Media: Traversal Scavenger Hunt

## Overview

This intermediate-level lab presents a content management platform operated by
Cascade Digital Media. The application exposes three separate file download
endpoints, each vulnerable to directory traversal. Students must discover all
three endpoints, exploit each one to retrieve a hidden token fragment, and
assemble the complete flag.

## Learning Objectives

- Identify multiple download endpoints across different sections of a web app
- Exploit path traversal with varying directory depths
- Locate sensitive files in non-standard filesystem paths
- Combine extracted fragments into a final flag

## Architecture

| Service | Role | IP Offset |
|---------|------|-----------|
| webapp  | Flask content platform with three download endpoints | 21 |

## Endpoints

| Path | Parameter | Serves From |
|------|-----------|-------------|
| `/media/download` | `asset` | `/app/media/assets/` |
| `/docs/fetch` | `doc` | `/app/docs/` |
| `/api/export` | `report` | `/app/api/reports/` |

## Tokens

Three tokens are hidden on the filesystem. Students must find all three and
combine them in the format `OCR{token1_token2_token3}`.

## Duration

40 minutes with progressive hints at 15, 25, and 35 minutes.
