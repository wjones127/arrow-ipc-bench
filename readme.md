Sharing Arrow data between processes
================

These are some tests to compare different methods of sharing an Arrow
table between different processes.

![](readme_files/figure-gfm/share-time-1.png)

![](readme_files/figure-gfm/share-throughput-1.png)

    # A tibble: 3 × 5
      name                avg_time_sec min_time_sec avg_gbps max_gbps
      <chr>                      <dbl>        <dbl>    <dbl>    <dbl>
    1 flight_export              3.28        2.80      0.468    0.531
    2 plasma_export              0.118       0.0851   15.5     17.5  
    3 sharedmemory_export        0.187       0.130     9.57    11.4  

![](readme_files/figure-gfm/retrieve-time-1.png)

    # A tibble: 3 × 3
      name                avg_time_sec min_time_sec
      <chr>                      <dbl>        <dbl>
    1 flight_export           3.69        2.72     
    2 plasma_import           0.000131    0.0000250
    3 sharedmemory_import     0.000166    0.0000432

## How to run

First start the plasma server

``` shell
plasma_store -m 1000000000 -s /tmp/plasma
```

Then, start the flight server

``` shell
python flight_server.py
```

Then run the share benchmarks

Finally, run the retrieve benchmarks:
