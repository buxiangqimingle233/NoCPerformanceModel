# NoCPerformanceModel
A numpy-based performance model for on-chip networks

## Structure
* Arguments of architecture and tasks are specified in *Configuration/your_config_file.json*
* Input task graphs should be stored in *Data/*, with format as (src, dst, vol), seperated by comma.

## How to use
### - cmd
* Command: 
  ```python Driver/Driver.py config_name```
* Noted that config_name is just the name of the configuration file, instead of path, e.g. "baseline.json"

### - other python script
* Import Driver.SDriver.Driver into your programme
* Instantiate a Driver with the name of configuration file, e.g. 
  ```d = SDriver.Driver("baseline.json")```

## Employ your own Estimator or CongManager
* Your own estimator and congestion manager should inherient from VirEstimator and CongManager respectively
* Put your estimator in *Estimator/* and congestion manager in *CongManager*