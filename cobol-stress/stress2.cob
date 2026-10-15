       IDENTIFICATION DIVISION.
       PROGRAM-ID. STRESS2.
      * Stress test: an EXEC CICS block, typical of mainframe online code.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-MSG            PIC X(20) VALUE "HELLO".
       PROCEDURE DIVISION.
       MAIN-PARA.
           EXEC CICS
              SEND TEXT FROM(WS-MSG)
           END-EXEC
           GOBACK.
