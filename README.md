# QuickCSF

A fast, adaptive approach to estimating contrast sensitivity function parameters across multiple eccentricities and stimulus orientations.

This implmentation is based on:

> Lesmes, L. A., Lu, Z. L., Baek, J., & Albright, T. D. (2010). Bayesian adaptive estimation of the contrast sensitivity function: The quick CSF method. *Journal of vision*, 10(3), 17-17.

Special thanks to Dr. Tianshi Lu at Wichita State University for providing a Matlab implemenation of the fundamental algorithm and Dr. Rui Ni at Wichita State University for the motivation.

## Dependencies
~~~~
$ pip3 install -e .
~~~~
Requires:
* `numpy`
* `qtpy`
* Qt bindings (via `PySide2`, `PyQt5`, `PySide`, or `PyQt`)

Optional (for simulation visuals):
* `matplotlib`

## Usage
### Measuring CSF
~~~~
$ python -m QuickCSF.py --help
usage: app.py [-h] [-sid SESSIONID] [-d DISTANCE_MM]
                   [--instructionsFile INSTRUCTIONSFILE]
                   [--controller.trialsPerBlock CONTROLLER.TRIALSPERBLOCK]
                   [--controller.blockCount CONTROLLER.BLOCKCOUNT]
                   [--controller.fixationDuration CONTROLLER.FIXATIONDURATION]
                   [--controller.stimulusDuration CONTROLLER.STIMULUSDURATION]
                   [--controller.maskDuration CONTROLLER.MASKDURATION]
                   [--controller.interStimulusInterval CONTROLLER.INTERSTIMULUSINTERVAL]
                   [--controller.feedbackDuration CONTROLLER.FEEDBACKDURATION]
                   [--controller.waitForReady] [-minc STIM.MINCONTRAST]
                   [-maxc STIM.MAXCONTRAST] [-cr STIM.CONTRASTRESOLUTION]
                   [-minf STIM.MINFREQUENCY] [-maxf STIM.MAXFREQUENCY]
                   [-fr STIM.FREQUENCYRESOLUTION] [--stim.size STIM.SIZE]

optional arguments:
  -h, --help            show this help message and exit
  -sid SESSIONID, --sessionID SESSIONID
                        A unique string to identify this observer/session
  -d DISTANCE_MM, --distance_mm DISTANCE_MM
                        Distance (mm) from the display to the observer
  --instructionsFile INSTRUCTIONSFILE
                        A plaintext file containing the instructions
  --controller.trialsPerBlock CONTROLLER.TRIALSPERBLOCK
                        Number of trials in each block
  --controller.blockCount CONTROLLER.BLOCKCOUNT
                        Number of blocks
  --controller.fixationDuration CONTROLLER.FIXATIONDURATION
                        How long (seconds) the fixation stimulus is displayed
  --controller.stimulusDuration CONTROLLER.STIMULUSDURATION
                        How long (seconds) the stimulus is displayed
  --controller.maskDuration CONTROLLER.MASKDURATION
                        How long (seconds) the stimulus mask is displayed
  --controller.interStimulusInterval CONTROLLER.INTERSTIMULUSINTERVAL
                        How long (seconds) a blank is displayed between stimuli
  --controller.feedbackDuration CONTROLLER.FEEDBACKDURATION
                        How long (seconds) feedback is displayed
  --controller.waitForReady
                        Wait for the participant to indicate they are ready for the next trial
  -minc STIM.MINCONTRAST, --stim.minContrast STIM.MINCONTRAST
                        The lowest contrast value to measure (0.0-1.0)
  -maxc STIM.MAXCONTRAST, --stim.maxContrast STIM.MAXCONTRAST
                        The highest contrast value to measure (0.0-1.0)
  -cr STIM.CONTRASTRESOLUTION, --stim.contrastResolution STIM.CONTRASTRESOLUTION
                        The number of contrast steps
  -minf STIM.MINFREQUENCY, --stim.minFrequency STIM.MINFREQUENCY
                        The lowest frequency value to measure (cycles per degree)
  -maxf STIM.MAXFREQUENCY, --stim.maxFrequency STIM.MAXFREQUENCY
                        The highest frequency value to measure (cycles per degree)
  -fr STIM.FREQUENCYRESOLUTION, --stim.frequencyResolution STIM.FREQUENCYRESOLUTION
                        The number of frequency steps
  --stim.size STIM.SIZE
                        Gabor patch size in (degrees)
~~~~

### Simulate and visualize an evaluation
~~~~
$ python -m QuickCSF.simulate --help
usage: simulate.py [-h] [-n TRIALS] [--imagePath IMAGEPATH] [-perfect]
                   [-minc MINCONTRAST] [-maxc MAXCONTRAST]
                   [-cr CONTRASTRESOLUTION] [-minf MINFREQUENCY]
                   [-maxf MAXFREQUENCY] [-fr FREQUENCYRESOLUTION]
                   [-s TRUEPEAKSENSITIVITY] [-f TRUEPEAKFREQUENCY]
                   [-b TRUEBANDWIDTH] [-d TRUEDELTA]

optional arguments:
  -h, --help            show this help message and exit
  -n TRIALS, --trials TRIALS
                        Number of trials to simulate
  --imagePath IMAGEPATH
                        Where to save images
  -perfect, --usePerfectResponses
                        Whether to simulate perfect responses, rather than probablistic ones
  -minc MINCONTRAST, --minContrast MINCONTRAST
                        The lowest contrast value to measure (0.0-1.0)
  -maxc MAXCONTRAST, --maxContrast MAXCONTRAST
                        The highest contrast value to measure (0.0-1.0)
  -cr CONTRASTRESOLUTION, --contrastResolution CONTRASTRESOLUTION
                        The number of contrast steps
  -minf MINFREQUENCY, --minFrequency MINFREQUENCY
                        The lowest frequency value to measure (cycles per degree)
  -maxf MAXFREQUENCY, --maxFrequency MAXFREQUENCY
                        The highest frequency value to measure (cycles per degree)
  -fr FREQUENCYRESOLUTION, --frequencyResolution FREQUENCYRESOLUTION
                        The number of frequency steps
  -s TRUEPEAKSENSITIVITY, --truePeakSensitivity TRUEPEAKSENSITIVITY
                        True peak sensitivity
  -f TRUEPEAKFREQUENCY, --truePeakFrequency TRUEPEAKFREQUENCY
                        True peak frequency
  -b TRUEBANDWIDTH, --trueBandwidth TRUEBANDWIDTH
                        True bandwidth
  -d TRUEDELTA, --trueDelta TRUEDELTA
                        True delta truncation
~~~~