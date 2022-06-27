/** ==================================================================
 * cros2_common.cxx
 * Common utility functions
 **/

#include "cros2_common.hpp"

 /** ----------------------------------------------------------------
  * tstamp_get()
  * utility timestamp getter
  **/
void tstamp_get(timespec *tStamp)
{
#ifdef WIN32
    timespec_get(tStamp, TIME_UTC);
#else
    clock_gettime(CLOCK_REALTIME, tStamp);
#endif
    return;
}
