       IDENTIFICATION DIVISION.
       PROGRAM-ID. ORDERPRG.
      * Sample program for the Graphify COBOL experiment.
      * Mirrors the Python sample: create an order, look up a user,
      * call a separate payment program.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-USER-ID        PIC 9(5) VALUE 101.
       01 WS-PRODUCT-ID     PIC 9(5) VALUE 501.
       01 WS-USER-NAME      PIC X(20).
       01 WS-STATUS         PIC X(20).
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM GET-USER
           PERFORM PROCESS-PAYMENT
           PERFORM SHOW-RESULT
           STOP RUN.
       GET-USER.
           MOVE "Demo User" TO WS-USER-NAME.
       PROCESS-PAYMENT.
           CALL "PAYMENT" USING WS-USER-ID WS-PRODUCT-ID WS-STATUS.
       SHOW-RESULT.
           DISPLAY "User:   " WS-USER-NAME
           DISPLAY "Status: " WS-STATUS.
