# clean-project-board

A rather hacky python script to clean up old issues from our github project
board.

The project ID is currently hardcoded. It looks for items in the "Done" and
"Tombstoned" states which have not been updated in the last 6 months, and
archives them on the board.

Usage:

```shell
pip install -r requirements.txt
export GITHUB_TOKEN=<personal gh token>
./query.py
```
