
# Pokemon Showdown Replay Parser

Analyzer class that can parse replays for Singles and VGC/Doubles matches given a battle log



## Usage/Examples

```python
from analyzer import Analyzer

with open("example_logs/battlelog12345.txt") as file:
    data = file.read().splitlines()

summary = analyzer.analyze_replay(data)
```


## License

[MIT](https://github.com/Auxowave/Pokemon-Showdown-Replay-Parser/blob/main/LICENSE)

