# NoCPerformanceModel
A numpy-based performance model for on-chip networks.

## Structure
* Arguments of architecture and tasks are specified in *Configuration/your_config_file.json*
* Input task graphs should be stored in *Data/*, with format as (src, dst, vol), seperated by comma, see *Data/Sample.txt* for an example.

## How to use
### - cmd
* Command: 
  ```python Driver/Driver.py config_name```
* Noted that config_name is just the name of the configuration file, instead of full path, e.g. "baseline.json"

### - other python script
* Import Driver.SDriver.Driver into your program.
* Instantiate a Driver with the name of configuration file and call execute function, e.g. 
  ```
  dr = SDriver.Driver("baseline.json")
  dr.execute()
  ```

## Employ your own Estimator or CongManager
* Your own estimator and congestion manager should inherient from *Estimator/VirEstimator* and *CongManager/VirCongManager* respectively.
* Put your estimator in *Estimator* and congestion manager in *CongManager* directories correspondingly.
