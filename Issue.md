# Common issue
## Error: ENOENT: no such file or directory, open 'C:\Users\USERNAME\AppData\Local\Programs\Zalo\Zalo-25.5.3\resources\app.asar.unpacked\native\nativelibs\index.js'
### Why?
This error occurs because when Electron launches an app packaged with ASAR, native modules or certain files that cannot be loaded from inside the archive are placed in a separate directory called app.asar.unpacked. If, after extracting or modifying app.asar, you do not also provide the corresponding files in app.asar.unpacked (such as native/nativelibs/index.js), Electron continues to look for them in that directory and throws an ENOENT error if they are missing. This commonly happens if you only extract app.asar without copying over the app.asar.unpacked directory, or if you replace app.asar with a folder but do not include all the required files that were originally unpacked.
This error also occurs when Zalo just updated, happened to me on 25.5.3.
### Fix
The only way to fix this problem is to reinstall Zalo with the lastest version, then run the script again and it should word with no problem.
