use std::io;

fn main() {
    println!("Guess the number!");

    println!("Please input your guess:");

    let mut guess = String::new();
    io::stdin()
        .read_line(&mut guess)
        .expect("Failed to read line");
    // unsecure: read_line does not validate the input whether it's a valid number
    // .unwrap() vs .expect() ??

    println!("You guessed: {guess}");
}
