       IDENTIFICATION DIVISION.
       PROGRAM-ID. STRESS1.
      * Stress test: constructs that are awkward for static analysis.
      * PERFORM THRU, PERFORM UNTIL / VARYING, inline PERFORM, GO TO,
      * a copybook, a CALL whose program name is in a variable, and a
      * CALL to a program that is not part of the scanned files.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY CUSTREC.
       01 WS-PROG-NAME      PIC X(8) VALUE "PAYMENT".
       01 WS-COUNT          PIC 9(2) VALUE 0.
       01 WS-I              PIC 9(2) VALUE 0.
       01 WS-DATA           PIC X(20) VALUE SPACES.
       PROCEDURE DIVISION.
       MAIN-PARA.
           PERFORM INIT-PARA
           PERFORM STEP-A THRU STEP-C
           PERFORM LOOP-PARA UNTIL WS-COUNT > 2
           PERFORM LOOP-PARA VARYING WS-I FROM 1 BY 1 UNTIL WS-I > 2
           PERFORM 2 TIMES
              DISPLAY "INLINE LOOP"
           END-PERFORM
           PERFORM DYN-CALL-PARA
           GO TO EXIT-PARA.
       INIT-PARA.
           MOVE "CUSTOMER" TO CUST-NAME.
       STEP-A.
           DISPLAY "STEP A".
       STEP-B.
           DISPLAY "STEP B".
       STEP-C.
           DISPLAY "STEP C".
       LOOP-PARA.
           ADD 1 TO WS-COUNT.
       DYN-CALL-PARA.
           CALL WS-PROG-NAME USING WS-DATA
           CALL "UNKNOWN1" USING WS-DATA.
       EXIT-PARA.
           STOP RUN.
