---
layout: post
title: Reading and writing using the new Rust IO library
category: posts

---

When the re-write of the `std::io` module landed in Rust [1.0.0-alpha.2][alpha2], there were a lot of changes to the way you read/write to a file. I'll cover some simple examples and probably make edits in the future to add more fancy stuff.

> **Disclaimer:** At the time of writing this, `std::io` is still a work in progress! I'm also currently learning this new library as I go along, so there may be errors on my behalf as well!

# Reading from a file

Reading to a file can be done in two ways (both really simple). I'll talk about one way here and the second a little later.

``` rust
let file = match File::open("test_file.txt") {
	Ok(file) => file,
	Err(..)  => panic!("room"),
}
```
<br>
`File::open` by default gives you `Read` permissons, so you can create a [`BufReader`][bufreader] from that.

``` rust
let mut reader = BufReader::new(&file);

// read_line takes reads a line and writes to a string, so we give it one.
let buffer_string = &mut String::new();
reader.read_line(buffer_string);
println!("We read a new line: {}", buffer_string);
```
<br>

# Writing to a file

### Permissons

A simple example for writing to a file is to start by creating your [`Path`][path], and an [`OpenOptions`][openoptions]. An `OpenOptions` is how you provide the file permissons and that you would need to read or write to a file appropriately.

``` rust
let mut options = OpenOptions::new();
// We want to write to our file as well as append new data to it.
options.write(true).append(true);
```
<br>

You can also add `.read(true)` for read permissions as an alternate way to read from the file. Although, the interesting part about `OpenOptions` is that you can re-use the options set for multiple files:

``` rust
// We can create a Path
let path = Path::new("test_file.txt");

// or we can also just use a string slice:
let path2 = "test_file2.txt";

// We create file options to write
let mut options = OpenOptions::new();
options.write(true)

// Both of these should be valid
let file: Result<File, Error> = options.open(path);
let file2: Result<File, Error> = options.open(path2);
```
<br>
### The actual writing bit

So now that we have the permissons setup correctly, we can create a [`BufWriter`][bufwriter] to actually write to the file. I've added a match statement to unwrap the unlike the previous snippet:

``` rust
let file = match options.open(&path) {
    Ok(file) => file,
    Err(..) => panic!("at the Disco"),
};

// We create a buffered writer from the file we get
let mut writer = BufWriter::new(&file);
// Then we write to the file. write_all() calls flush() after the write as well.
writer.write_all(b"test\n");
```
<br>

# Conclusion

In my examples, I've used separate buffers but you can use a [`BufStream`][bufstream] as well to get all the same features combined.

[alpha2]: http://blog.rust-lang.org/2015/02/20/Rust-1.0-alpha2.html
[path]: http://doc.rust-lang.org/std/path/index.html
[openoptions]: http://doc.rust-lang.org/std/fs/struct.OpenOptions.html
[bufreader]: http://doc.rust-lang.org/std/io/struct.BufReader.html
[bufwriter]: http://doc.rust-lang.org/std/io/struct.BufWriter.html
[bufstream]: http://doc.rust-lang.org/std/io/struct.BufStream.html
