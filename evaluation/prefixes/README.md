# Get List of Prefixes

Download bview from (http://data.ris.ripe.net/rrc00/) and use bgpdump to get a text file of all the routes.

```bash
$ zcat < latest-bview.gz | bgpdump -m - > routes.log
```

Then, extract the prefixes from the route advertisements, sort them and remove all duplicates:

```bash 
$ cat routes.log | awk -F "|" '{print $6}' |  sort | uniq > prefixes.log
```
