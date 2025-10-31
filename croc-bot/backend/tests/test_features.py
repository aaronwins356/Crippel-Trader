from datetime import datetime, timedelta, timezone

import numpy as np

from croc.data.features import FeaturePipeline, LiveFeatureState, features_from_ticks
from croc.models.types import Tick


def generate_ticks(count: int) -> list[Tick]:
    base = datetime.now(tz=timezone.utc)
    return [
        Tick(
            timestamp=base + timedelta(minutes=i),
            symbol="BTC/USDT",
            bid=100 + i * 0.1,
            ask=100 + i * 0.1 + 0.2,
            last=100 + i * 0.1 + 0.1,
            volume=1 + (i % 5),
        )
        for i in range(count)
    ]


def test_feature_parity_live_vs_offline():
    ticks = generate_ticks(100)
    pipeline = FeaturePipeline(fast_window=5, slow_window=10, vol_window=6)
    offline = features_from_ticks(ticks, pipeline)
    live = LiveFeatureState(pipeline, max_length=100)
    online = []
    for tick in ticks:
        feat = live.update(tick)
        if feat is not None:
            online.append(feat)
    assert len(online) == len(offline) - (pipeline.slow_window - 1)
    np.testing.assert_allclose(np.array(online), offline[pipeline.slow_window - 1 :], atol=1e-6)
