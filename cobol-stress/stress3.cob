       IDENTIFICATION DIVISION.
       PROGRAM-ID. STRESS3.
      * Stress test: an EXEC SQL block, typical of DB2 batch code.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-COUNT          PIC 9(5) VALUE 0.
       PROCEDURE DIVISION.
       MAIN-PARA.
           EXEC SQL
              SELECT COUNT(*) INTO :WS-COUNT FROM CUSTOMERS
           END-EXEC
           GOBACK.
