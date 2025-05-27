# Common issue
## Error: ENOENT: no such file or directory, open 'C:\Users\USERNAME\AppData\Local\Programs\Zalo\Zalo-25.5.3\resources\app.asar.unpacked\native\nativelibs\index.js'
### Affect Range
Every Zalo version (Unsure).
### Why?
This error occurs because when Electron launches an app packaged with ASAR, native modules or certain files that cannot be loaded from inside the archive are placed in a separate directory called app.asar.unpacked. If, after extracting or modifying app.asar, you do not also provide the corresponding files in app.asar.unpacked (such as native/nativelibs/index.js), Electron continues to look for them in that directory and throws an ENOENT error if they are missing. This commonly happens if you only extract app.asar without copying over the app.asar.unpacked directory, or if you replace app.asar with a folder but do not include all the required files that were originally unpacked.\
This error also occurs when Zalo just updated, happened to me on 25.5.3.
### Fix
The only way to fix this problem is to reinstall Zalo with the lastest version, then run the script again and it should work with no problem.
## Can not send clipboard images
### Affect range
Zalo >= 25.5.2\
Installer 1.0.0
### Why?
Well I am not sure why but Zalo can not to send clipboard images when app.asar is modified and repacked.
### Fix
To resolve this issue, we no longer unpack, modify, and repack the `app.asar` file. Instead, we unpack it once, make our modifications directly within the unpacked folder, then rename the original `app.asar` to something like `app.asar.bak` as a backup, and finally rename the modified folder to `app.asar`. This simpler method avoids repacking complications and resolves the issue. \
As of version 1.0.1 and above, this fix has been implemented and the problem is no longer present.
\
All credit to [ncdai](https://github.com/ncdai) for the solution !
# Report issue
To report any issue that you encountered, please report the issue to
[zalo-custom-reaction-PC-issue-tracker](https://github.com/fynrae/zalo-custom-reaction-PC-issue-tracker)!
