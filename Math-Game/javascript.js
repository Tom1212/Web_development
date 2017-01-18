var playing = false;
var score;
var action;
var timeremaining;
var correctAnswer;

// if we click on the start/reset
document.getElementById("startreset").onclick = function(){
     //if we are playing
    if(playing == true){
        //reload page
        location.reload();
    }else{//if we are not playing
        
        playing = true;
        hide("gameOver");
        
        //set score to 0
        score = 0;
        document.getElementById("scoreValue").innerHTML = score;
        
        //show countdown box
        show("timeremaining");
    
        // set timeremaining to 60 sec to initial
        timeremaining = 60;
        document.getElementById("timeremainingValue").innerHTML = timeremaining;
        
        //change button to reset
        document.getElementById("startreset").innerHTML = "Reset Game";
        
        //start countdown
        startCountdown();
        
        //generate new question and answer
        generateQA();
    }
}

//Clicking on an answer box
for(i=1; i<5; i++){
    document.getElementById("box"+i).onclick = function(){
    //check if we are playing     
    if(playing == true){//yes
        if(this.innerHTML == correctAnswer){
        //correct answer
            
            //increase score by 1
            score++;
            document.getElementById("scoreValue").innerHTML = score;
            //hide wrong box and show correct box
            hide("wrong");
            show("correct");
            setTimeout(function(){
                hide("correct");   
            }, 1000);
            
            //Generate new Q&A
            generateQA();
            
        }else{
        //wrong answer
            hide("correct");
            show("wrong");
            setTimeout(function(){
                hide("wrong");   
            }, 1000);
        }
    }
}   
}

function startCountdown(){
    action = setInterval(function(){
        timeremaining -= 1;
        document.getElementById("timeremainingValue").innerHTML = timeremaining;
        
        if(timeremaining == 0){
            stopCountdown();
            show("gameOver");
            document.getElementById("gameOver").innerHTML = "<p>Game Over!</p><p>Your score is " + score + ".</p>";
            
            hide("timeremaining");
            hide("correct");
            hide("wrong");
            playing = false;
            
            document.getElementById("startreset").innerHTML = "Start Game";
            
        }
        
    }, 1000);
}

function stopCountdown(){
    clearInterval(action);
}

function hide(Id){
    document.getElementById(Id).style.display = "none";
}

function show(Id){
    document.getElementById(Id).style.display = "block";
}

// questions
function generateQA(){
    // excluded 0
    var x = 1 + Math.round(9*Math.random());
    var y = 1 + Math.round(9*Math.random());
    
    correctAnswer = x * y;
    document.getElementById("question").innerHTML = x + "x" + y;
    
    // total is 4 boxes
    var correctPosition = 1 + Math.round(3*Math.random());
    
    // set correctAnswer to box
    document.getElementById("box" + correctPosition).innerHTML = correctAnswer;
    
    var answers = [correctAnswer];
    
    //fill other boxes with wrong answers
    for(i=1; i<5; i++){
        if(i != correctPosition){
            var wrongAnswer;
            
            // there is a very good example for using do..while
            do{
                wrongAnswer = (1 + Math.round(9*Math.random())) * (1 + Math.round(9*Math.random()));
                
            }while(answers.indexOf(wrongAnswer)> -1){// ensure all results are not same
                document.getElementById("box" + i).innerHTML = wrongAnswer;
                answers.push(wrongAnswer);
            }
   
        }
    }
}






