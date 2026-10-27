SURVIVOR - Windows build package (no local Python required)

1. Extract this ZIP. The extracted folder itself contains survivor_theme_boss_music_graphics.py and the hidden .github folder.
2. On GitHub, open your empty repository and choose "uploading an existing file".
3. Upload the PY FILE, .gitignore, and the .github/workflows/build-windows.yml file so that the paths are at repository root exactly as in this ZIP. Do not upload a parent folder containing them. If folder drag/drop does not keep .github, create the folders .github/workflows on GitHub and upload build-windows.yml there.
4. Commit the files. Open Actions and run "Build Windows Game" (or wait for the push-triggered workflow).
5. When it finishes successfully, open the workflow run and download the SURVIVOR-Windows artifact. Extract it and send the entire SURVIVOR folder to your friend.

The Windows build happens on GitHub; you do not need Python installed on your own computer.
