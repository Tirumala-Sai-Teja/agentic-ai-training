to run the code:
1. create a .env file if not
2. update the groq api key in the .env file
3. Update the test files folder location in the agent invoke parameter
    eg: "Testfiles/"
    output =app.invoke(
        {
        "message":"",
        "status":"",
        "directory_path":<folderPath>,
        "files":[],
        'fileContent':{},
        "fileTypes":{},
        "currentFile" :{},
        "humanReview":{},
        "auditLog":[]
        })
4. Note: Already ran the 29 test files, hence the log, DB and irrelevant file json are updated with run details.
5. To run and see the output for fresh set of test files, delete the auditLog.json, cease_desist.db and irrelevant_archive.json files.
6. run the main_HITL.py