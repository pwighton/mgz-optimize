# MGZ optimize

🚧 WORK IN PROGRESS 🚧

Optimize [MGZ files](https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/MghFormat) for web-based viewing by
- Converting them to ints, if appropriate
- Converting them to the smallest compatible int type supported by MGZ (UCHAR, SHORT or INT)
- Setting the intent code to denote label data, if appropriate; See:
  - [C definition of intent codes](https://github.com/freesurfer/freesurfer/blob/d557ae6dd9d2e83e12851c89572c39cae4a50a7f/utils/mri.cpp#L469)
  - [python defintion of intent codes](https://github.com/freesurfer/surfa/blob/0ab851a36703458023d9ada9cac466d045829399/surfa/core/framed.py#L11)


Setup:
- v3.8.13 ensures it's the same version as fspython

```
conda create --name mgz-optimize python=3.8.13
conda activate mgz-optimize
pip install ./requirements.txt
```

Todo:
  - reference actual intent code (sf.core.framed.FramedArrayIntents) instead of hard coded values
  - Verify `mgz_label_files` list
  
