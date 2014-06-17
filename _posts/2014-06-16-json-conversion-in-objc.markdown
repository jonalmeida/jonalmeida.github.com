---
layout: post
title: JSON object conversion into different types with Objective-C
category: posts

---

When dealing with network APIs that use JSON, I find myself constantly converting objects from one form to another for data manipulation or storage. In Objective-C we're lucky to have such rich libraries that make life easier. Although, it does tend to get tedious when you start converting an NSDictionary to an NSData, or NSString to NSData, and so on. I wanted to make it easier so I had a one liner option to do this.

An Objective-C Category is something I just learned about recently. It lets you extend a classes functionality without subclassing or having the source to it (!). It seemed easy enough to solve my problems using this.

I wrote a small class that extends `NSData`, `NSString` and `NSDictionary` giving them class methods to return a JSON object from one type to another.

---

|     Type     | NSData | NSString | NSDictionary |
|--------------|------|--------|------------|
|    NSData    |  n/a|        |            |
|   NSString   |      | n/a       |            |
| NSDictionary |      |        |    n/a      |

## Usage

Using the category class is simple. Simply drop the `JsonEncoder.h` and `JsonEncoder.m` into your project. And use it similar to the examples below.

### Converting NSString
A string that is correctly escaped and in the right syntax:

``` objective-c
// A string that we want to convert to a dictionary
NSString * json_str = @"{\"Key\":\"Value\"}";
// Using the extended class..
NSDictionary * dict = [NSDictionary dictionaryFromString:json_str];
// OR
NSData * data = [NSData dataWithString:json_str];
```
<br>
### Converting NSDictionary
We can take a dictionary and convert that easily:

``` objective-c
// A simple initialized dictionary
NSDictionary * dict = [NSDictionary dictionaryWithObjectsAndKeys:
							@"Value",@"Key", nil];
// Using the extended class..
NSString * json_str = [NSString stringFromDictionary:dict];
// OR
NSData * data = [NSData dataFromDictionary:dict];
```
<br>
### Converting NSData
NSData also works:

``` objective-c
// Let's assume we already have an NSData object!
// We can convert it using the extended class..
NSDictionary * dict = [NSDictionary dictionaryFromData:data];
// OR
NSString * json_str = [NSString stringFromData:data];
```
<br>
You can find the source [here][1].

[1]: https://github.com/jonalmeida/JsonConverter