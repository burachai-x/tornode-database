# tornode-database

An automatically updated database of running [Tor](https://www.torproject.org/) network relay nodes.  
Data is fetched daily from the [Onionoo](https://metrics.torproject.org/onionoo.html) API and committed to this repository.

## Schedule

The sync workflow runs every day at **20:17 UTC**.

## Files

All CSV files are stored in the [`torlist-db/`](./torlist-db/) directory.

| File | Description |
|------|-------------|
| [`latest.all.csv`](./torlist-db/latest.all.csv) | Every running relay |
| [`latest.guards.csv`](./torlist-db/latest.guards.csv) | Guard (entry) nodes only |
| [`latest.exits.csv`](./torlist-db/latest.exits.csv) | Exit nodes only |

### CSV format

```
fingerprint,ipaddr,port
000004ACBB9D29BCBA17256BB35928DDBFC8ABA9,152.53.144.50,8443
000004ACBB9D29BCBA17256BB35928DDBFC8ABA9,2a0a:4cc0:c1:2aac::1,8443
```

A relay with multiple OR addresses appears on multiple rows (one per address).

## Data source

- **API:** `https://onionoo.torproject.org/details?running=true&type=relay`
- **Docs:** [Onionoo protocol](https://metrics.torproject.org/onionoo.html)

## Run locally

Requires Python 3.10+. No external dependencies.

```bash
python fetch_tor_nodes.py
# CSV files are written to torlist-db/
```

## Acknowledgements

Inspired by [alireza-rezaee/tor-nodes](https://github.com/alireza-rezaee/tor-nodes) (C# implementation).

## License

MIT
