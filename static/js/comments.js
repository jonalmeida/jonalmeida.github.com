/*
  Comment loading for the `comments` component in
  templates/components/comments.html.

  The component renders the container as
  `<section id="comments" data-host data-username data-status-id>`, and this
  file reads those attributes. The script lives here, and not inline in the
  component, because Zola's markdown parser ends a raw HTML block at the first
  blank line: an inline script was cut in half and the remainder was rendered
  as a highlighted code block.
*/
(function () {
  const container = document.getElementById("comments");
  if (!container) {
    return;
  }

  const host = container.dataset.host;
  const username = container.dataset.username;
  const statusId = container.dataset.statusId;

  function escapeHtml(unsafe) {
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function emojify(input, emojis) {
    let output = input;

    emojis.forEach(emoji => {
      let picture = document.createElement("picture");

      let source = document.createElement("source");
      source.setAttribute("srcset", escapeHtml(emoji.url));
      source.setAttribute("media", "(prefers-reduced-motion: no-preference)");

      let img = document.createElement("img");
      img.className = "emoji";
      img.setAttribute("src", escapeHtml(emoji.static_url));
      img.setAttribute("alt", `:${ emoji.shortcode }:`);
      img.setAttribute("title", `:${ emoji.shortcode }:`);
      img.setAttribute("width", "20");
      img.setAttribute("height", "20");

      picture.appendChild(source);
      picture.appendChild(img);

      output = output.replace(`:${ emoji.shortcode }:`, picture.outerHTML);
    });

    return output;
  }

  function loadCssFile(path) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.type = 'text/css';
    link.href = path; // relative path to your CSS file
    document.head.appendChild(link);
  }

  function loadComments() {
    let purifyPromise = import("/assets/js/purify.min.js");
    let cssPromise = loadCssFile("/comments.css");

    let commentsWrapper = document.getElementById("comments-wrapper");
    document.getElementById("load-comment").innerHTML = "Loading";
    fetch(`https://${ host }/api/v1/statuses/${ statusId }/context`)
      .then(function(response) {
        return response.json();
      })
      .then(function(data) {
        let descendants = data['descendants'];
        if(
          descendants &&
          Array.isArray(descendants) &&
          descendants.length > 0
        ) {
          commentsWrapper.innerHTML = "";

          descendants.forEach(function(status) {
            /* For debugging */
            /* console.log(descendants) */
            if( status.account.display_name.length > 0 ) {
              status.account.display_name = escapeHtml(status.account.display_name);
              status.account.display_name = emojify(status.account.display_name, status.account.emojis);
            } else {
              status.account.display_name = status.account.username;
            };

            let instance = "";
            if( status.account.acct.includes("@") ) {
              instance = status.account.acct.split("@")[1];
            } else {
              instance = host;
            }

            const isReply = status.in_reply_to_id !== statusId;

            let op = false;
            if( status.account.acct == username ) {
              op = true;
            }

            status.content = emojify(status.content, status.emojis);

            let avatarSource = document.createElement("source");
            avatarSource.setAttribute("srcset", escapeHtml(status.account.avatar));
            avatarSource.setAttribute("media", "(prefers-reduced-motion: no-preference)");

            let avatarImg = document.createElement("img");
            avatarImg.className = "avatar";
            avatarImg.setAttribute("src", escapeHtml(status.account.avatar_static));
            avatarImg.setAttribute("alt", `@${ status.account.username }@${ instance } avatar`);

            let avatarPicture = document.createElement("picture");
            avatarPicture.appendChild(avatarSource);
            avatarPicture.appendChild(avatarImg);

            let avatar = document.createElement("a");
            avatar.className = "avatar-link";
            avatar.setAttribute("href", status.account.url);
            avatar.setAttribute("rel", "external nofollow");
            avatar.setAttribute("title", `View profile at @${ status.account.username }@${ instance }`);
            avatar.appendChild(avatarPicture);

            let instanceBadge = document.createElement("a");
            instanceBadge.className = "instance";
            instanceBadge.setAttribute("href", status.account.url);
            instanceBadge.setAttribute("title", `@${ status.account.username }@${ instance }`);
            instanceBadge.setAttribute("rel", "external nofollow");
            instanceBadge.textContent = instance;

            let display = document.createElement("span");
            display.className = "display";
            display.setAttribute("itemprop", "author");
            display.setAttribute("itemtype", "http://schema.org/Person");
            display.innerHTML = status.account.display_name;

            let header = document.createElement("header");
            header.className = "author";
            header.appendChild(display);
            header.appendChild(instanceBadge);

            let permalink = document.createElement("a");
            permalink.setAttribute("href", status.url);
            permalink.setAttribute("itemprop", "url");
            permalink.setAttribute("title", `View comment at ${ instance }`);
            permalink.setAttribute("rel", "external nofollow");
            permalink.textContent = new Date( status.created_at ).toLocaleString('en-US', {
              dateStyle: "long",
              timeStyle: "short",
            });

            let timestamp = document.createElement("time");
            timestamp.setAttribute("datetime", status.created_at);
            timestamp.appendChild(permalink);

            let main = document.createElement("main");
            main.setAttribute("itemprop", "text");
            main.innerHTML = status.content;

            let interactions = document.createElement("footer");
            if(status.favourites_count > 0) {
              let faves = document.createElement("a");
              faves.className = "faves";
              faves.setAttribute("href", `${ status.url }/favourites`);
              faves.setAttribute("title", `Favorites from ${ instance }`);
              faves.textContent = status.favourites_count;

              interactions.appendChild(faves);
            }

            let comment = document.createElement("article");
            comment.id = `comment-${ status.id }`;
            comment.className = isReply ? "comment comment-reply" : "comment";
            comment.setAttribute("itemprop", "comment");
            comment.setAttribute("itemtype", "http://schema.org/Comment");
            comment.appendChild(avatar);
            comment.appendChild(header);
            comment.appendChild(timestamp);
            comment.appendChild(main);
            comment.appendChild(interactions);

            if(op === true) {
              comment.classList.add("op");

              avatar.classList.add("op");
              avatar.setAttribute(
                "title",
                "Blog post author; " + avatar.getAttribute("title")
              );

              instanceBadge.classList.add("op");
              instanceBadge.setAttribute(
                "title",
                "Blog post author: " + instanceBadge.getAttribute("title")
              );
            }

            Promise.all([purifyPromise, cssPromise]).then(() => {
              commentsWrapper.innerHTML += DOMPurify.sanitize(comment.outerHTML);
            });

          });
        } else {
          commentsWrapper.innerHTML = "<p>No comments.</p>";
        }
        // Makes the button update more user-perceivable.
        setTimeout(() => {
          document.getElementById("load-comment").innerHTML = "Reload comments";
        }, 300);
      });
    }

  document.getElementById("load-comment").addEventListener("click", loadComments);
})();
