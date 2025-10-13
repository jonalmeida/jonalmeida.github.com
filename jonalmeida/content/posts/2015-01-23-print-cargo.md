---
layout: post
title: Enabling print statements in Cargo tests
categories: posts
aliases: ['posts/2015/01/23/print-cargo']
---

When writing tests in Cargo, you sometimes need to debug failures and print statements are a great way to do that. When you run `cargo test` the output shows details about which tests pass or fail but filters out the stdout information.

The you can enable this by running tests with `-- --nocapture` like this:

~~~ bash

$ cargo test -- --nocapture

~~~
<br>

Here is an example of what a test would look like:

~~~ rust

#[test]
fn new_linked_list() {
    let mut list: super::LinkedList<String> = super::LinkedList::new();
    list.add("first".to_string());
    println!("Value added: {}", list.head.unwrap().payload);
}

~~~
<br>
When we run this with the `no capture` flag:

~~~ bash

     Running target/algorithms-43e2eed4b681635b

running 3 tests
test datastructures::linkedlist::node_new ... ok
Value added: first
test datastructures::linkedlist::node_payload ... ok
test datastructures::linkedlist::tests::new_linked_list ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured
~~~

<br>

Notice that the print statement is before the test passes (a false positive since I haven't added an assertion), but it gets intertwined with our other tests which are running in parrallel. This can be annoying to see if you have a longer list of tests. We can remove that as well by only running the specific test that we want:

~~~ bash

$ cargo test -- --nocapture datastructures::linkedlist::tests::new_linked_list

~~~
<br>

We then see:

~~~ bash

     Running target/algorithms-43e2eed4b681635b

running 1 test
Value added: first
test datastructures::linkedlist::tests::new_linked_list ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured

~~~