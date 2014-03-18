---
layout: post
title: Android HTTP POST and GET requests stored in JSON
category: posts

---

In my current project, I'm currently working on making an Android client send simple HTTP POST and GET requests for data to a web API. I finally managed to get it working using the [HTTP Apache library][1].

> **Note:** I un-indented the code so it would fit better on the page even though it looks a bit ugly. You might be better off copying it to your text editor to read it better.


``` java
HttpClient httpclient = new DefaultHttpClient();
HttpPost httppost = new HttpPost("http://dogecoin.com/api");
HttpResponse httpresponse = null;

final Thread t = new Thread() {
    public void run() {

    Looper.prepare();
    ArrayList<NameValuePair> postParameters;

    postParameters = new ArrayList<NameValuePair>();
    postParameters.add(
        new BasicNameValuePair("key", "value"));
    postParameters.add(
        new BasicNameValuePair("double", Double.toString(123)));
    postParameters.add(
        new BasicNameValuePair("float", Float.toString(123.04)));

    try {
        httppost.setEntity(new UrlEncodedFormEntity(postParameters));
        // reset to null before making a new post if it's being reused
        httpresponse = null;
        httpresponse = httpclient.execute(httppost);
    } catch (IOException e1) {
        e1.printStackTrace();
    }

    // Checking response
    if(httpresponse!=null){

    try {

        // Get the data in the entity
        BufferedReader reader = new BufferedReader(
            new InputStreamReader(
                httpresponse.getEntity().getContent(), "UTF-8")
        );

        StringBuilder builder = new StringBuilder();
        for (String line = null; (line = reader.readLine()) != null;) {
            builder.append(line).append("\n");
        }

        JSONTokener tokener = new JSONTokener(builder.toString());
        JSONObject finaljson = new JSONObject(tokener);

        Log.v("JSON OUTPUT: ", finaljson.toString());

    } catch (IOException e) {
        e.printStackTrace();
    } catch (JSONException e) {
        e.printStackTrace();
    }

    }

    Looper.loop(); //Loop in the message queue
    
    }
};

t.start();
```
<br>

To explain some parts that might not seem obvious, we use `new UrlEncodedFormEntity()` to URL encode the name-value pairs to be `http://dogecoin.com/api?key=value`. The encoder handles the character conversion so you can enter it in it's original ASCII form.

Any non-string type needs to be converted into a string in order to be encoded. This is mainly because `BasicNameValuePair` handles only strings.

After executing the HttpPost, if our response is going to be JSON encoded, we can loop through the response to hold within a string, and then use the `JSONTokener` to build a `JSONObject`. You ought to output the response into the logs the first few times just to verify it is correct.

> **Side Note:** To remain consistent you could always store your POST message in JSON as well and create a `getNameValueArrayList()` to easily output the object. However, that solely depends on your needs.
> 
 
[1]: http://developer.android.com/reference/org/apache/http/package-summary.html